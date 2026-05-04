"""
FraxVerse · 每日收盘扫描 Pipeline

交易日 16:30 后执行（A股收盘后），完整流程：
1. 全市场粗筛（screen_strategy1 + screen_strategy2）
2. 五维度评分（score_candidates）
3. 前15名写入 stock_pool（pass_coarse=True）
4. 前5名推给 Agent 讨论（run_daily_analysis）
5. 输出汇总结果并推送到微信队列
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.db.session import get_session

logger = logging.getLogger(__name__)

# ── 收盘扫描时间窗口 ──────────────────────────────────────────
# A股收盘15:00，16:00后数据基本齐了
SCAN_WINDOW_START = dtime(16, 0)   # 最早可执行时间
SCAN_WINDOW_END = dtime(17, 30)    # 最迟执行时间


def is_trade_day(trade_date: date | None = None) -> bool:
    """判断是否为交易日（简单判断：非周末）"""
    if trade_date is None:
        trade_date = date.today()
    # 周一=0, 周日=6
    return trade_date.weekday() < 5


def is_in_scan_window(now: datetime | None = None) -> bool:
    """当前时间是否在收盘扫描窗口内"""
    if now is None:
        from datetime import datetime
        now = datetime.now()
    t = now.time()
    return SCAN_WINDOW_START <= t <= SCAN_WINDOW_END


def _get_trade_date() -> str:
    """获取当前交易日字符串 YYYY-MM-DD"""
    return date.today().isoformat()


def _load_strategy_config(db: Any) -> dict:
    """从 DB 加载策略配置"""
    try:
        from src.strategy.screener import _get_strategy_config as load_cfg
        return load_cfg()
    except Exception as exc:
        logger.warning("策略配置加载失败（使用默认值）: %s", exc)
        return {}


def _screen_and_score() -> list[dict]:
    """
    全市场粗筛 + 评分

    Returns:
        scored dicts 列表（前15名），含 ScoredCandidate 所有字段
    """
    from src.strategy.scorer import score_candidates
    from src.strategy.screener import screen_strategy1, screen_strategy2

    config = _load_strategy_config(None)
    trade_date = _get_trade_date()

    logger.info("[pipeline] 策略一（底部反转）粗筛...")
    c1 = screen_strategy1(config)
    logger.info("  策略一结果: %d 只", len(c1))

    logger.info("[pipeline] 策略二（趋势跟踪）粗筛...")
    c2 = screen_strategy2(config)
    logger.info("  策略二结果: %d 只", len(c2))

    all_candidates = c1 + c2
    if not all_candidates:
        logger.warning("[pipeline] 无任何候选标的")
        return []

    logger.info("[pipeline] 五维度评分（共 %d 只候选）...", len(all_candidates))
    scored = score_candidates(
        candidates=all_candidates,
        trade_date=trade_date,
    )
    logger.info("[pipeline] 评分完成，前15名如下：")
    for s in scored[:15]:
        logger.info("  %s %s | 总分: %.1f | %s", s.stock_code, s.stock_name, s.score_total, s.reason)

    # 转 dict 方便后续用
    results = []
    for s in scored[:15]:
        results.append({
            "stock_code": s.stock_code,
            "stock_name": s.stock_name,
            "strategy_type": s.strategy_type,
            "score_total": float(s.score_total),
            "score_volume": float(s.score_volume),
            "score_fund": float(s.score_fund),
            "score_sentiment": float(s.score_sentiment),
            "score_mainforce": float(s.score_mainforce),
            "score_logic": float(s.score_logic),
            "reason": s.reason,
            "dimensions": {k: v.to_dict() if hasattr(v, "to_dict") else str(v) for k, v in s.dimensions.items()},
        })

    return results


def _write_to_stock_pool(scored_list: list[dict], db: Any) -> int:
    """
    将评分结果写入 stock_pool 表

    Returns:
        写入行数
    """
    from src.db.models import StockPool

    trade_date_str = _get_trade_date()
    count = 0

    for s in scored_list:
        try:
            # 检查是否已存在
            existing = db.query(StockPool).filter(
                StockPool.date == trade_date_str,
                StockPool.stock_code == s["stock_code"],
                StockPool.strategy_type == s["strategy_type"],
            ).first()

            if existing:
                # 更新评分（如果之前只是粗筛）
                existing.score_total = Decimal(str(s["score_total"]))
                existing.score_volume = Decimal(str(s["score_volume"]))
                existing.score_fund = Decimal(str(s["score_fund"]))
                existing.score_sentiment = Decimal(str(s["score_sentiment"]))
                existing.score_mainforce = Decimal(str(s["score_mainforce"]))
                existing.score_logic = Decimal(str(s["score_logic"]))
                existing.pass_coarse = True
            else:
                rec = StockPool(
                    date=trade_date_str,
                    stock_code=s["stock_code"],
                    strategy_type=s["strategy_type"],
                    pass_coarse=True,
                    score_total=Decimal(str(s["score_total"])),
                    score_volume=Decimal(str(s["score_volume"])),
                    score_fund=Decimal(str(s["score_fund"])),
                    score_sentiment=Decimal(str(s["score_sentiment"])),
                    score_mainforce=Decimal(str(s["score_mainforce"])),
                    score_logic=Decimal(str(s["score_logic"])),
                )
                db.add(rec)
            count += 1
        except Exception as exc:
            logger.error("写入 stock_pool 失败 [%s]: %s", s["stock_code"], exc)

    db.commit()
    logger.info("[pipeline] stock_pool 写入 %d 条", count)
    return count


def _run_agent_discussion(db: Any, scored_list: list[dict]) -> list[dict]:
    """
    将前5名推给 Agent 讨论

    Returns:
        Agent 讨论结果列表
    """
    top5 = scored_list[:5]
    if not top5:
        return []

    stock_codes = [s["stock_code"] for s in top5]
    logger.info("[pipeline] Agent 讨论标的: %s", ", ".join(stock_codes))

    try:
        from src.agent.orchestrator import AgentOrchestrator
        from src.agent.utils import (
            get_active_risk_events_fn,
            get_agent_history_fn,
            get_all_weights_fn,
            get_daily_volume_fn,
            get_kline_close_fn,
            get_market_state_fn,
            get_pending_records_fn,
            get_stock_pool_fn,
            get_weights_fn,
            save_decisions_fn,
            save_discussions_fn,
            update_outcome_fn,
            update_weight_db_fn,
            update_weights_fn,
        )

        orchestrator = AgentOrchestrator(
            get_stock_pool_fn=get_stock_pool_fn,
            get_market_state_fn=get_market_state_fn,
            get_weights_fn=get_weights_fn,
            get_active_risk_events_fn=get_active_risk_events_fn,
            get_daily_volume_fn=get_daily_volume_fn,
            get_agent_history_fn=get_agent_history_fn,
            save_decisions_fn=save_decisions_fn,
            save_discussions_fn=save_discussions_fn,
            update_weights_fn=update_weights_fn,
            get_all_weights_fn=get_all_weights_fn,
            update_weight_db_fn=update_weight_db_fn,
            update_outcome_fn=update_outcome_fn,
            get_pending_records_fn=get_pending_records_fn,
            get_kline_close_fn=get_kline_close_fn,
        )

        results = orchestrator.run_daily_analysis(stock_codes=stock_codes)
        logger.info("[pipeline] Agent 讨论完成: %d 只", len(results))

        # 更新 stock_pool 的 Agent 决策字段
        for r in results:
            db.execute(
                text("""
                    UPDATE stock_pool
                    SET final_decision = :decision,
                        final_score = :score,
                        reject_reason = :reason,
                        agent_scores = :agent_scores::jsonb
                    WHERE date = (SELECT MAX(date) FROM stock_pool)
                      AND stock_code = :code
                """),
                {
                    "decision": r.decision.value if hasattr(r.decision, "value") else r.decision,
                    "score": Decimal(str(r.total_score)),
                    "reason": r.decision_reason or "",
                    "agent_scores": json.dumps(r.agent_votes, ensure_ascii=False),
                    "code": r.stock_code,
                },
            )
        db.commit()

        return [r.model_dump() for r in results]

    except Exception as exc:
        logger.error("[pipeline] Agent 讨论失败: %s", exc)
        return []


def _push_notification(results: list[dict]) -> None:
    """推送通知到微信队列"""
    from src.notification.wechat_queue import push_wechat_text

    if not results:
        push_wechat_text(
            "📋 收盘扫描完成\n今日无符合条件的候选标的。",
            source="pipeline",
        )
        return

    lines = ["📋 收盘扫描报告\n"]
    for r in results[:5]:
        decision = r.get("decision", "hold")
        score = r.get("total_score", 0)
        code = r.get("stock_code", "")
        reason = r.get("decision_reason", "") or ""
        emoji = "✅" if decision == "buy" else "⏸️" if decision == "hold" else "❌"
        lines.append(f"{emoji} {code} 决策:{decision} 评分:{score:.1f}")
        if reason:
            lines.append(f"   理由: {reason[:100]}")

    push_wechat_text("\n".join(lines), source="pipeline")


def run_close_market_scan(
    trade_date: str | None = None,
    skip_agent: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    收盘扫描主入口

    Args:
        trade_date: 交易日 YYYY-MM-DD，默认今天
        skip_agent: 跳过 Agent 讨论（仅做粗筛+评分）
        dry_run: 仅打印日志，不写入 DB

    Returns:
        summary dict:
            - trade_date: 交易日
            - candidates_count: 粗筛总数
            - scored_count: 评分总数
            - top5_codes: 前5代码列表
            - agent_results: Agent 讨论结果列表
            - status: ok / skipped（非交易日/非窗口）/ error
    """
    today = date.today()
    if trade_date:
        try:
            today = date.fromisoformat(trade_date)
        except ValueError:
            trade_date = today.isoformat()

    trade_date_str = trade_date or today.isoformat()

    # 交易日检查
    if not is_trade_day(today):
        logger.info("[pipeline] %s 非交易日，跳过", trade_date_str)
        return {"trade_date": trade_date_str, "status": "skipped", "reason": "非交易日"}

    # 时间窗口检查（仅实时运行时检查，单次执行跳过）
    if not dry_run:
        if not is_in_scan_window():
            logger.warning(
                "[pipeline] 当前时间 %s 不在扫描窗口 %s-%s 内",
                datetime.now().strftime("%H:%M"),
                SCAN_WINDOW_START.strftime("%H:%M"),
                SCAN_WINDOW_END.strftime("%H:%M"),
            )

    logger.info("=" * 60)
    logger.info("[pipeline] 收盘扫描启动 | 交易日: %s", trade_date_str)
    logger.info("=" * 60)

    # 步骤1: 全市场粗筛 + 评分
    scored = _screen_and_score()
    if not scored:
        _push_notification([])
        return {
            "trade_date": trade_date_str,
            "candidates_count": 0,
            "scored_count": 0,
            "top5_codes": [],
            "status": "ok",
            "message": "无候选标的",
        }

    # 步骤2: 写入 stock_pool
    if not dry_run:
        db = get_session()
        try:
            written = _write_to_stock_pool(scored, db)

            # 步骤3: Agent 讨论（前5名）
            agent_results = []
            if not skip_agent:
                agent_results = _run_agent_discussion(db, scored)
        finally:
            db.close()
    else:
        written = 0
        agent_results = []

    top5_codes = [s["stock_code"] for s in scored[:5]]
    logger.info("[pipeline] 收盘扫描完成 | 候选: %d | 写入: %d | Top5: %s",
                len(scored), written, ", ".join(top5_codes))

    # 步骤4: 推送通知到微信队列
    if not dry_run:
        _push_notification(agent_results)

    return {
        "trade_date": trade_date_str,
        "candidates_count": len(scored),
        "scored_count": len(scored),
        "top5_codes": top5_codes,
        "agent_results": agent_results,
        "status": "ok",
    }
