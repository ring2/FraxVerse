"""
FraxVerse · 事件订阅器

将 EventBus 事件分发给对应的处理模块。
所有 EventBus 的消费端统一在此注册。

启动方式：
    from src.eventbus.subscribers import register_all_subscribers
    register_all_subscribers()
"""

from __future__ import annotations

import logging

from src.eventbus.bus import Event, EventType, get_bus

logger = logging.getLogger(__name__)


# ── 止损事件 → 微信推送 ────────────────────────────────────


def _handle_stop_loss(event: Event) -> None:
    """止损触发 → 微信推送告警"""
    data = event.data
    try:
        from src.notification.wechat import get_notifier

        notifier = get_notifier()
        from decimal import Decimal

        notifier.send_stop_loss_alert(
            stock_code=data.get("stock_code", ""),
            trigger_price=Decimal(str(data.get("trigger_price", 0))),
            cost_price=Decimal(str(data.get("cost_price", 0))),
            loss_pct=Decimal(str(data.get("loss_pct", 0))),
            reason=data.get("reason", ""),
        )
        logger.info("Stop loss alert sent for %s", data.get("stock_code"))
    except Exception as exc:
        logger.warning("Failed to send stop loss alert: %s", exc)


# ── 止盈事件 → 微信推送 ────────────────────────────────────


def _handle_stop_profit(event: Event) -> None:
    """止盈触发 → 微信推送通知"""
    data = event.data
    try:
        from src.notification.wechat import get_notifier

        notifier = get_notifier()
        from decimal import Decimal

        notifier.send_stop_profit_alert(
            stock_code=data.get("stock_code", ""),
            trigger_price=Decimal(str(data.get("trigger_price", 0))),
            cost_price=Decimal(str(data.get("cost_price", 0))),
            profit_pct=Decimal(str(data.get("profit_pct", 0))),
            reason=data.get("reason", ""),
        )
        logger.info("Stop profit alert sent for %s", data.get("stock_code"))
    except Exception as exc:
        logger.warning("Failed to send stop profit alert: %s", exc)


# ── 风控告警 → 微信推送 + 数据库记录 ──────────────────────


def _handle_risk_alert(event: Event) -> None:
    """风控告警 → 推送通知 + 写入 RiskEvents 表"""
    data = event.data
    # 推送通知
    try:
        from src.notification.wechat import get_notifier

        notifier = get_notifier()
        notifier.send_risk_warning(
            alert_type=data.get("alert_type", "unknown"),
            current_value=data.get("current_value", 0),
            threshold=data.get("threshold", 0),
            description=data.get("description", ""),
        )
        logger.info("Risk alert sent: %s", data.get("alert_type"))
    except Exception as exc:
        logger.warning("Failed to send risk alert: %s", exc)

    # 写入风控事件表
    try:
        from datetime import date

        from src.db.models import RiskEvents
        from src.db.session import get_session

        with get_session() as db:
            risk_event = RiskEvents(
                event_type=data.get("alert_type", "RISK_ALERT"),
                event_level=data.get("level", "MEDIUM"),
                trigger_value=float(data.get("current_value", 0)),
                threshold_value=float(data.get("threshold", 0)),
                trigger_reason=data.get("description", ""),
                action_taken=data.get("action_taken", "none"),
                action_detail={
                    "source": event.source,
                    "event_id": event.event_id,
                },
                trade_date=date.today(),
            )
            db.add(risk_event)
            db.commit()
            logger.info("Risk event logged: %s", risk_event.id)
    except Exception as exc:
        logger.warning("Failed to log risk event: %s", exc)


# ── 注册所有订阅 ──────────────────────────────────────────


def register_all_subscribers() -> None:
    """注册所有事件处理器到 EventBus"""
    bus = get_bus()

    bus.subscribe(EventType.STOP_LOSS_TRIGGERED, _handle_stop_loss)
    bus.subscribe(EventType.STOP_PROFIT_TRIGGERED, _handle_stop_profit)
    bus.subscribe(EventType.RISK_ALERT, _handle_risk_alert)

    logger.info("All event subscribers registered")
