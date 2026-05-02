"""
FraxVerse · 每日收盘分析脚本

在 cronjob 中被 Hermes Agent 调用，完成：
1. 检查今日决策数据
2. 汇总资产/持仓/信号状态
3. 生成结构化报告
4. （由 Hermes cron 引擎自动发送到微信）

用法（内部）：
    python scripts/daily_report.py

输出：打印 Markdown 格式的报告，cron 引擎自动转发到微信。
"""

import os
import sys

# 确保能找到 src 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, text

from src.db.models import (
    AgentDecision,
    Notifications,
    Positions,
    TradeMode,
    TradeOrders,
)
from src.db.session import get_session


def fetch_today_data() -> dict[str, Any]:
    """拉取今日关键数据"""
    today = date.today()
    result: dict[str, Any] = {
        "date": today.isoformat(),
        "mode": "SIMULATION",
        "positions": [],
        "today_orders": [],
        "today_decisions": [],
        "today_notifications": [],
        "summary": {},
    }

    with get_session() as db:
        # 交易模式
        mode = db.query(TradeMode).first()
        if mode:
            result["mode"] = mode.current_mode

        # 持仓
        positions = db.query(Positions).filter(Positions.total_volume > 0).all()
        for p in positions:
            result["positions"].append({
                "stock_code": p.stock_code,
                "volume": int(p.total_volume or 0),
                "cost_price": float(p.cost_price or 0),
                "market_value": float(p.market_value or 0),
                "unrealized_pnl": float(p.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(p.unrealized_pnl_pct or 0),
            })

        # 今日订单
        orders = (
            db.query(TradeOrders)
            .filter(
                func.date(TradeOrders.created_at) == today,
            )
            .order_by(TradeOrders.created_at.desc())
            .limit(20)
            .all()
        )
        for o in orders:
            result["today_orders"].append({
                "stock_code": o.stock_code,
                "direction": o.direction,
                "volume": int(o.volume or 0),
                "status": o.status,
                "reason": o.reason or "",
            })

        # 今日决策
        decisions = (
            db.query(AgentDecision)
            .filter(AgentDecision.date == today)
            .order_by(AgentDecision.created_at.desc())
            .limit(10)
            .all()
        )
        for d in decisions:
            result["today_decisions"].append({
                "stock_code": d.stock_code,
                "decision": d.decision,
                "total_score": float(d.total_score or 0),
                "reason": d.decision_reason or "",
            })

        # 今日未读通知
        notifications = (
            db.query(Notifications)
            .filter(
                func.date(Notifications.created_at) == today,
                Notifications.is_read == False,
            )
            .order_by(Notifications.created_at.desc())
            .limit(10)
            .all()
        )
        for n in notifications:
            result["today_notifications"].append({
                "event_type": n.event_type,
                "title": n.title,
                "priority": n.priority,
            })

        # 汇总
        total_asset = Decimal("0")
        total_pnl = Decimal("0")
        for p in positions:
            total_asset += p.market_value or Decimal("0")
            total_pnl += p.unrealized_pnl or Decimal("0")

        result["summary"] = {
            "position_count": len(positions),
            "total_asset": float(total_asset),
            "total_unrealized_pnl": float(total_pnl),
            "today_order_count": len(result["today_orders"]),
            "today_decision_count": len(result["today_decisions"]),
            "unread_notification_count": len(result["today_notifications"]),
        }

    return result


def format_report(data: dict[str, Any]) -> str:
    """格式化为 Markdown 报告"""
    s = data["summary"]
    lines = [
        f"📈 **碎片宇宙 · 每日报告**",
        f"📅 {data['date']} | 模式: `{data['mode']}`",
        "",
        "━━━ 资产概览 ━━━",
        f"• 总资产: ¥{s['total_asset']:,.2f}",
        f"• 未实现盈亏: ¥{s['total_unrealized_pnl']:+,.2f}",
        f"• 当前持仓: {s['position_count']} 只",
        "",
        "━━━ 今日活动 ━━━",
        f"• 新订单: {s['today_order_count']} 笔",
        f"• 新决策: {s['today_decision_count']} 条",
        f"• 未读通知: {s['unread_notification_count']} 条",
    ]

    if data["positions"]:
        lines.append("")
        lines.append("━━━ 持仓明细 ━━━")
        for p in data["positions"]:
            emoji = "📗" if p["unrealized_pnl"] >= 0 else "📕"
            lines.append(
                f"{emoji} {p['stock_code']}: {p['volume']}股 "
                f"成本{p['cost_price']:.2f} "
                f"盈亏{p['unrealized_pnl']:+,.2f} ({p['unrealized_pnl_pct']:+.2f}%)"
            )

    if data["today_decisions"]:
        lines.append("")
        lines.append("━━━ 今日决策 ━━━")
        for d in data["today_decisions"]:
            action_emoji = "🟢" if d["decision"] == "buy" else "🔴"
            lines.append(f"{action_emoji} {d['stock_code']} 评分{d['total_score']:.1f}: {d['reason'][:50]}")

    if data["today_notifications"]:
        lines.append("")
        lines.append("━━━ 待处理通知 ━━━")
        for n in data["today_notifications"]:
            lines.append(f"• {n['title']}")

    lines.append("")
    lines.append("---")
    lines.append(f"_自动生成于 {datetime.now().strftime('%H:%M')}_")

    return "\n".join(lines)


def main():
    """主入口：拉取数据 → 生成报告 → 打印到 stdout（cron引擎自动转发）"""
    try:
        data = fetch_today_data()
        report = format_report(data)
        print(report)
        print()
        pos_count = data["summary"]["position_count"]
        print(f"[INFO] 报告完成: {data['date']}, 持仓{pos_count}只", file=sys.stderr)
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
