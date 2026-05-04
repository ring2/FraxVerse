"""
FraxVerse · Redis 微信消息队列

后端所有需要推送到用户微信的消息，统一写入 Redis List。
Hermes Agent 独立轮询脚本从中读取并调用 send_message 发送。

架构：
  后端 (WeChatNotifier / EventBus / 任何模块)
    ↓  LPUSH queue:wechat_messages
  Redis List (queue:wechat_messages)
    ↓  BLPOP
  hermes_weixin_redis_poller.py (Hermes 侧)
    ↓  send_message("weixin", text=...)
  微信消息 ✓
"""

import json
import logging
from typing import Any

import redis

logger = logging.getLogger(__name__)

# Redis List 键名
QUEUE_KEY = "queue:wechat_messages"


def _get_redis() -> redis.Redis:
    """获取指向 FraxVerse Redis 的连接"""
    from src.config import settings

    url = settings.REDIS_URL
    return redis.Redis.from_url(url, decode_responses=True)


def push_wechat_text(
    text: str,
    *,
    source: str = "system",
    dedup_key: str | None = None,
) -> bool:
    """推送纯文本消息到微信队列

    Args:
        text: 消息内容（纯文本，支持 Markdown）
        source: 来源模块标识，用于追踪
        dedup_key: 可选去重键，相同键 5 分钟内不重复入队

    Returns:
        是否成功入队
    """
    try:
        r = _get_redis()

        # 去重检查
        if dedup_key:
            recent = r.get(f"dedup:{dedup_key}")
            if recent:
                logger.info(f"去重跳过: {dedup_key}")
                return False

        payload = {
            "type": "text",
            "text": text,
            "source": source,
            "dedup_key": dedup_key,
        }
        r.lpush(QUEUE_KEY, json.dumps(payload, ensure_ascii=False))

        # 写去重标记（5分钟过期）
        if dedup_key:
            r.setex(f"dedup:{dedup_key}", 300, "1")

        logger.info(f"微信消息已入队 [source={source}]: {text[:60]}...")
        return True

    except Exception as e:
        logger.error(f"微信消息入队失败: {e}")
        return False


def push_wechat_trade_signal(
    stock_code: str,
    action: str,
    price: float,
    quantity: int,
    reason: str,
) -> bool:
    """推送交易信号到微信队列"""
    text = (
        f"📊 交易信号: {action} {stock_code}\n"
        f"价格: {price:.2f}\n"
        f"数量: {quantity}\n"
        f"原因: {reason}"
    )
    return push_wechat_text(
        text,
        source="trade_signal",
        dedup_key=f"trade_signal:{stock_code}:{action}",
    )


def push_wechat_stop_loss(
    stock_code: str,
    trigger_price: float,
    cost_price: float,
    pnl_pct: float,
    reason: str,
) -> bool:
    """推送止损告警到微信队列"""
    text = (
        f"⚠️ 止损触发: {stock_code}\n"
        f"触发价: {trigger_price:.2f}\n"
        f"成本价: {cost_price:.2f}\n"
        f"浮盈: {pnl_pct:.2f}%\n"
        f"原因: {reason}"
    )
    return push_wechat_text(
        text,
        source="stop_loss",
        dedup_key=f"stop_loss:{stock_code}",
    )


def push_wechat_stop_profit(
    stock_code: str,
    current_price: float,
    cost_price: float,
    pnl_pct: float,
    stage: str,
) -> bool:
    """推送止盈告警到微信队列"""
    text = (
        f"💰 止盈触发: {stock_code}\n"
        f"当前价: {current_price:.2f}\n"
        f"成本价: {cost_price:.2f}\n"
        f"浮盈: {pnl_pct:.2f}%\n"
        f"阶段: {stage}"
    )
    return push_wechat_text(
        text,
        source="stop_profit",
        dedup_key=f"stop_profit:{stock_code}:{stage}",
    )


def push_wechat_risk_warning(title: str, content: str) -> bool:
    """推送风险预警到微信队列"""
    text = (
        f"🔴 风险预警: {title}\n"
        f"{content}"
    )
    return push_wechat_text(
        text,
        source="risk_warning",
        dedup_key=f"risk:{title}",
    )


def push_wechat_system_error(error_msg: str, module: str) -> bool:
    """推送系统异常到微信队列"""
    text = (
        f"🚨 系统异常: {module}\n"
        f"错误: {error_msg}"
    )
    return push_wechat_text(text, source="system_error")


def push_wechat_daily_report(report: dict[str, Any]) -> bool:
    """推送每日报告到微信队列"""
    text = (
        f"📈 每日报告\n"
        f"总资产: {report.get('total_asset', 'N/A')}\n"
        f"当日盈亏: {report.get('daily_pnl', 'N/A')}\n"
        f"持仓数: {report.get('position_count', 0)}\n"
        f"今日交易: {report.get('trade_count', 0)}笔"
    )
    return push_wechat_text(
        text,
        source="daily_report",
    )
