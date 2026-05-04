"""
FraxVerse · 微信通知服务

消息写入 Redis 消息队列，由 Hermes Agent 轮询发送到微信。
功能：
1. 通知记录持久化到 notifications 表
2. 消息写入 Redis List（queue:wechat_messages）
3. Hermes 侧 weixin_redis_poller.py 读取并调用 send_message 发送
4. 支持去重（dedup_key）
5. 支持邮件兜底（当 Hermes 队列不可用时作为备选通道）
"""
import logging
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Notifications
from src.db.session import get_session

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    TRADE_SIGNAL = "trade_signal"       # 交易信号
    STOP_LOSS = "stop_loss"             # 止损告警
    STOP_PROFIT = "stop_profit"         # 止盈告警
    RISK_WARNING = "risk_warning"       # 风险预警
    SYSTEM_ERROR = "system_error"       # 系统异常
    DAILY_REPORT = "daily_report"       # 每日报告
    STRATEGY_UPDATE = "strategy_update" # 策略更新


class NotificationPriority(str, Enum):
    """优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class WeChatNotifier:
    """
    微信推送服务

    通过 Hermes Agent 的 weixin 通道发送消息到用户微信。
    消息格式支持：纯文本、Markdown（微信部分支持）。
    """

    def __init__(self, user_id: int = 1):
        """
        Args:
            user_id: 接收通知的用户ID（默认1，单用户系统）
        """
        self.user_id = user_id

    def send(
        self,
        event_type: NotificationType,
        title: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        content_json: dict | None = None,
        dedup_key: str | None = None,
    ) -> Notifications | None:
        """
        发送通知

        Args:
            event_type: 通知类型
            title: 标题
            content: 内容
            priority: 优先级
            content_json: 结构化数据
            dedup_key: 去重键（相同键24小时内不重复发送）

        Returns:
            Notifications 记录，或 None（去重跳过时）
        """
        with get_session() as db:
            # 去重检查
            if dedup_key:
                existing = db.execute(
                    select(Notifications).where(
                        Notifications.dedup_key == dedup_key,
                        Notifications.push_status.in_(["pending", "sent"]),
                        Notifications.created_at >= datetime.now(UTC).replace(
                            hour=0, minute=0, second=0
                        ),
                    )
                ).scalar_one_or_none()

                if existing:
                    logger.info(f"去重跳过: {dedup_key}")
                    return None

            # 创建通知记录
            notification = Notifications(
                user_id=self.user_id,
                event_type=event_type.value,
                priority=priority.value,
                title=title,
                content=content,
                content_json=content_json or {},
                push_channel="wechat",
                push_status="pending",
                dedup_key=dedup_key,
            )
            db.add(notification)
            db.commit()

            # 实际发送（SIMULATION模式下只记录不发送）
            self._do_send(db, notification)

            return notification

    def _do_send(self, db: Session, notification: Notifications):
        """
        执行发送

        优先写入 Redis 消息队列（Hermes 轮询发送到微信），
        写入失败时降级为邮件兜底。
        """
        try:
            # 1. 尝试 Redis 队列（主要通道）
            message_text = (
                f"{notification.title}\n\n"
                f"{notification.content}"
            )
            sent_via_redis = self._push_to_redis_queue(notification, message_text)

            if sent_via_redis:
                notification.push_status = "sent"
                notification.push_channel = "wechat_queue"
                db.commit()
                logger.info(
                    f"通知已入队: [{notification.event_type}] {notification.title}"
                )
                return

            # 2. Redis 不可用 → 降级为邮件
            logger.warning("Redis 队列不可用，降级为邮件发送")
            self._send_email(notification)

            notification.push_status = "sent"
            notification.push_channel = "email"
            db.commit()
            logger.info(
                f"通知已发送（邮件兜底）: [{notification.event_type}] {notification.title}"
            )

        except Exception as e:
            notification.push_status = "failed"
            notification.retry_count += 1
            db.commit()
            logger.error(f"通知发送失败: {e}")

    def _push_to_redis_queue(
        self, notification: Notifications, text: str
    ) -> bool:
        """将通知写入 Redis 消息队列"""
        try:
            from src.notification.wechat_queue import push_wechat_text

            return push_wechat_text(
                text,
                source=notification.event_type,
                dedup_key=notification.dedup_key,
            )
        except Exception as exc:
            logger.warning("Redis 队列写入失败: %s", exc)
            return False

    def _send_email(self, notification: Notifications) -> bool:
        """通过邮件发送通知"""
        try:
            from src.notification.email_notifier import get_email_notifier

            notifier = get_email_notifier()
            priority = "urgent" if notification.priority == "urgent" else \
                       "high" if notification.priority == "high" else \
                       "normal"
            return notifier.send(
                title=notification.title,
                content=notification.content,
                priority=priority,
            )
        except Exception as exc:
            logger.warning("邮件推送失败: %s", exc)
            return False

    def send_trade_signal(
        self,
        stock_code: str,
        action: str,
        price: Decimal,
        quantity: int,
        reason: str,
    ):
        """发送交易信号"""
        return self.send(
            event_type=NotificationType.TRADE_SIGNAL,
            title=f"📊 交易信号: {action} {stock_code}",
            content=(
                f"股票: {stock_code}\n"
                f"操作: {action}\n"
                f"价格: {price}\n"
                f"数量: {quantity}\n"
                f"原因: {reason}"
            ),
            priority=NotificationPriority.HIGH,
            content_json={
                "stock_code": stock_code,
                "action": action,
                "price": float(price),
                "quantity": quantity,
                "reason": reason,
            },

        )

    def send_stop_loss_alert(
        self,
        stock_code: str,
        trigger_price: Decimal,
        cost_price: Decimal,
        pnl_pct: Decimal,
        reason: str,
    ):
        """发送止损告警"""
        return self.send(
            event_type=NotificationType.STOP_LOSS,
            title=f"⚠️ 止损触发: {stock_code}",
            content=(
                f"股票: {stock_code}\n"
                f"触发价: {trigger_price}\n"
                f"成本价: {cost_price}\n"
                f"浮盈: {pnl_pct:.2f}%\n"
                f"原因: {reason}"
            ),
            priority=NotificationPriority.URGENT,
            content_json={
                "stock_code": stock_code,
                "trigger_price": float(trigger_price),
                "cost_price": float(cost_price),
                "pnl_pct": float(pnl_pct),
                "reason": reason,
            },

        )

    def send_stop_profit_alert(
        self,
        stock_code: str,
        current_price: Decimal,
        cost_price: Decimal,
        pnl_pct: Decimal,
        stage: str,
    ):
        """发送止盈告警"""
        return self.send(
            event_type=NotificationType.STOP_PROFIT,
            title=f"💰 止盈触发: {stock_code}",
            content=(
                f"股票: {stock_code}\n"
                f"当前价: {current_price}\n"
                f"成本价: {cost_price}\n"
                f"浮盈: {pnl_pct:.2f}%\n"
                f"阶段: {stage}"
            ),
            priority=NotificationPriority.HIGH,
            content_json={
                "stock_code": stock_code,
                "current_price": float(current_price),
                "cost_price": float(cost_price),
                "pnl_pct": float(pnl_pct),
                "stage": stage,
            },
        )

    def send_risk_warning(
        self,
        title: str,
        content: str,
        risk_data: dict | None = None,
    ):
        """发送风险预警"""
        return self.send(
            event_type=NotificationType.RISK_WARNING,
            title=f"🔴 风险预警: {title}",
            content=content,
            priority=NotificationPriority.HIGH,
            content_json=risk_data or {},
        )

    def send_system_error(self, error_msg: str, module: str):
        """发送系统异常"""
        return self.send(
            event_type=NotificationType.SYSTEM_ERROR,
            title=f"🚨 系统异常: {module}",
            content=f"模块: {module}\n错误: {error_msg}",
            priority=NotificationPriority.URGENT,

        )

    def send_daily_report(self, report: dict):
        """发送每日报告"""
        return self.send(
            event_type=NotificationType.DAILY_REPORT,
            title=f"📈 每日报告 {datetime.now(UTC).date()}",
            content=(
                f"总资产: {report.get('total_asset', 'N/A')}\n"
                f"当日盈亏: {report.get('daily_pnl', 'N/A')}\n"
                f"持仓数: {report.get('position_count', 0)}\n"
                f"今日交易: {report.get('trade_count', 0)}笔"
            ),
            priority=NotificationPriority.NORMAL,
            content_json=report,

        )


# 便捷函数
def get_notifier(user_id: int = 1) -> WeChatNotifier:
    """获取通知器实例"""
    return WeChatNotifier(user_id=user_id)
