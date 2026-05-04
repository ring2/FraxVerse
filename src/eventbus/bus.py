"""
FraxVerse · 事件总线（EventBus）

基于 Redis Pub/Sub 的轻量事件驱动架构。
纯增量设计，不修改现有业务代码的调用方式。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

import redis

from src.config import settings

logger = logging.getLogger(__name__)


class EventType(Enum):
    """系统事件类型枚举"""

    STOP_LOSS_TRIGGERED = auto()
    """止损被触发"""
    STOP_PROFIT_TRIGGERED = auto()
    """止盈被触发"""
    POSITION_OPENED = auto()
    """新开仓"""
    POSITION_CLOSED = auto()
    """清仓离场"""
    RISK_ALERT = auto()
    """风控告警（回撤/连续亏损等）"""
    MARKET_EXTREME = auto()
    """极端行情"""
    TRADE_SIGNAL_GENERATED = auto()
    """新交易信号"""
    SYSTEM_ERROR = auto()
    """系统级错误"""


@dataclass
class Event:
    """事件数据单元"""

    event_type: EventType
    source: str
    data: dict
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class EventBus:
    """
    基于 Redis Pub/Sub 的事件总线。

    用法::

        bus = EventBus()
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, my_handler)
        bus.publish(Event(type=EventType.STOP_LOSS_TRIGGERED, source="monitor", data={...}))

    注意：
    - 当前使用同步 redis 客户端，publish 立即写入 Redis
    - subscribe 的 handler 在调用 subscribe() 后立即生效
    - 事件不持久化，Redis 重启后未消费的事件丢失（可接受）
    """

    # Redis 通道前缀
    CHANNEL_PREFIX = "fraxverse:events:"

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: redis.Redis | None = None
        self._handlers: dict[str, list[Callable]] = {}

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _channel(self, event_type: EventType) -> str:
        return f"{self.CHANNEL_PREFIX}{event_type.name.lower()}"

    # ── 发布 ─────────────────────────────────────────────────

    def publish(self, event: Event) -> None:
        """发布事件到 Redis 通道"""
        channel = self._channel(event.event_type)
        payload = {
            "event_type": event.event_type.name,
            "source": event.source,
            "data": event.data,
            "timestamp": event.timestamp,
            "event_id": event.event_id,
        }
        try:
            self.redis.publish(channel, json.dumps(payload, default=str))
            logger.debug("Published %s → %s [%s]", event.event_type.name, channel, event.event_id)
        except redis.RedisError as exc:
            logger.warning("Publish failed for %s: %s", event.event_type.name, exc)

    def publish_type(
        self,
        event_type: EventType,
        source: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """快捷发布：自动构造 Event 对象"""
        self.publish(Event(event_type=event_type, source=source, data=data or {}))

    # ── 订阅 ─────────────────────────────────────────────────

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """注册事件处理器"""
        key = self._channel(event_type)
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)
        logger.info("Subscribed %s → %s", event_type.name, handler.__name__)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """取消注册事件处理器"""
        key = self._channel(event_type)
        if key in self._handlers:
            self._handlers[key] = [h for h in self._handlers[key] if h is not handler]

    # ── 消费 ─────────────────────────────────────────────────

    def _on_message(self, raw: dict[str, Any]) -> None:
        """内部：收到 Redis 消息后分发给注册的 handler"""
        channel = raw.get("channel", "")
        if channel not in self._handlers:
            return
        try:
            payload = json.loads(raw.get("data", "{}"))
            event_type_name = payload.get("event_type", "")
            try:
                event_type = EventType[event_type_name]
            except KeyError:
                logger.warning("Unknown event type: %s", event_type_name)
                return
            event = Event(
                event_type=event_type,
                source=payload.get("source", "unknown"),
                data=payload.get("data", {}),
                timestamp=payload.get("timestamp", 0.0),
                event_id=payload.get("event_id", ""),
            )
            for handler in self._handlers[channel]:
                try:
                    handler(event)
                except Exception as exc:
                    logger.error("Handler %s failed: %s", handler.__name__, exc)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse event message: %s", exc)

    def listen(self, block: bool = False, timeout: float | None = None) -> None:
        """
        启动事件监听（阻塞模式）。

        在独立线程中运行，持续从 Redis 接收消息。
        调用 listen() 前需要先注册 handler（subscribe）。

        Args:
            block: 是否阻塞当前线程
            timeout: 单次 poll 超时（秒），None=无限等待
        """
        if not self._handlers:
            logger.warning("listen() called with no registered handlers")
            return

        pubsub = self.redis.pubsub()
        for channel in self._handlers:
            pubsub.subscribe(channel)
        logger.info("EventBus listening on %d channels", len(self._handlers))

        try:
            for message in pubsub.listen():
                if message.get("type") == "message":
                    self._on_message(message)
        except redis.RedisError as exc:
            logger.error("EventBus listen error: %s", exc)
        except KeyboardInterrupt:
            logger.info("EventBus listener stopped")
        finally:
            pubsub.close()


# ── 全局单例 ────────────────────────────────────────────────

_bus: EventBus | None = None


def get_bus() -> EventBus:
    """获取全局 EventBus 实例"""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
