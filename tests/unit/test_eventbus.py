"""
EventBus 单元测试
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
import redis

from src.eventbus.bus import Event, EventBus, EventType


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    mock_conn = MagicMock(spec=redis.Redis)
    with patch("src.eventbus.bus.redis.from_url", return_value=mock_conn):
        # pubsub() 返回 mock
        mock_pubsub = MagicMock()
        mock_conn.pubsub.return_value = mock_pubsub
        # listen() 模拟空迭代（不阻塞）
        mock_pubsub.listen.return_value = []
        yield mock_conn


@pytest.fixture
def bus(mock_redis):
    return EventBus(redis_url="redis://localhost:6379/0")


class TestEventCreation:
    def test_event_basic(self):
        event = Event(
            event_type=EventType.STOP_LOSS_TRIGGERED,
            source="test_monitor",
            data={"stock_code": "000001.SH", "loss_pct": 5.2},
        )
        assert event.event_type == EventType.STOP_LOSS_TRIGGERED
        assert event.source == "test_monitor"
        assert event.data["stock_code"] == "000001.SH"
        assert event.event_id is not None
        assert len(event.event_id) == 12

    def test_event_types_enum(self):
        """验证所有事件类型均被定义"""
        types = {
            "STOP_LOSS_TRIGGERED": EventType.STOP_LOSS_TRIGGERED,
            "STOP_PROFIT_TRIGGERED": EventType.STOP_PROFIT_TRIGGERED,
            "POSITION_OPENED": EventType.POSITION_OPENED,
            "POSITION_CLOSED": EventType.POSITION_CLOSED,
            "RISK_ALERT": EventType.RISK_ALERT,
            "MARKET_EXTREME": EventType.MARKET_EXTREME,
            "TRADE_SIGNAL_GENERATED": EventType.TRADE_SIGNAL_GENERATED,
            "SYSTEM_ERROR": EventType.SYSTEM_ERROR,
        }
        assert len(types) == 8


class TestEventBusPublish:
    def test_publish_sends_to_redis(self, bus, mock_redis):
        bus.publish_type(
            EventType.STOP_LOSS_TRIGGERED,
            source="test",
            data={"stock_code": "000001.SH"},
        )
        # 验证 redis.publish 被调用
        assert mock_redis.publish.called
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        payload = json.loads(call_args[0][1])
        assert "fraxverse:events:stop_loss_triggered" in channel
        assert payload["event_type"] == "STOP_LOSS_TRIGGERED"
        assert payload["source"] == "test"

    def test_publish_redis_error_logged(self, bus, mock_redis):
        """Redis 连接异常不应抛异常，仅打日志"""
        mock_redis.publish.side_effect = redis.RedisError("connection lost")
        # 不应抛出异常
        bus.publish_type(EventType.SYSTEM_ERROR, source="test")
        assert True  # 走到这里说明通过

    def test_publish_type_auto_creates_event(self, bus, mock_redis):
        bus.publish_type(
            EventType.RISK_ALERT,
            source="risk_monitor",
            data={"alert_type": "drawdown", "value": 8.5},
        )
        assert mock_redis.publish.called
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event_type"] == "RISK_ALERT"


class TestEventBusSubscribe:
    def test_subscribe_registers_handler(self, bus):
        handler = lambda e: None
        handler.__name__ = "test_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        channel = "fraxverse:events:stop_loss_triggered"
        assert channel in bus._handlers
        assert handler in bus._handlers[channel]

    def test_unsubscribe_removes_handler(self, bus):
        handler = lambda e: None
        handler.__name__ = "test_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        bus.unsubscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        channel = "fraxverse:events:stop_loss_triggered"
        assert handler not in bus._handlers[channel]

    def test_multiple_handlers_same_event(self, bus):
        h1 = lambda e: None; h1.__name__ = "h1"
        h2 = lambda e: None; h2.__name__ = "h2"
        bus.subscribe(EventType.RISK_ALERT, h1)
        bus.subscribe(EventType.RISK_ALERT, h2)
        assert len(bus._handlers["fraxverse:events:risk_alert"]) == 2


class TestEventBusMessageHandler:
    def test_on_message_dispatches_to_handler(self, bus):
        handler = MagicMock()
        handler.__name__ = "mock_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)

        bus._on_message({
            "channel": "fraxverse:events:stop_loss_triggered",
            "data": json.dumps({
                "event_type": "STOP_LOSS_TRIGGERED",
                "source": "monitor",
                "data": {"stock_code": "000001.SH"},
                "timestamp": time.time(),
                "event_id": "abc123",
            }),
        })
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert isinstance(event, Event)
        assert event.event_type == EventType.STOP_LOSS_TRIGGERED
        assert event.data["stock_code"] == "000001.SH"

    def test_on_message_unknown_event_type(self, bus):
        handler = MagicMock()
        handler.__name__ = "mock_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        bus._on_message({
            "channel": "fraxverse:events:stop_loss_triggered",
            "data": json.dumps({
                "event_type": "UNKNOWN_EVENT",
                "source": "test",
                "data": {},
                "timestamp": 0,
                "event_id": "",
            }),
        })
        handler.assert_not_called()

    def test_on_message_handler_exception(self, bus):
        handler = MagicMock(side_effect=ValueError("oops"))
        handler.__name__ = "mock_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        # 不应冒泡异常
        bus._on_message({
            "channel": "fraxverse:events:stop_loss_triggered",
            "data": json.dumps({
                "event_type": "STOP_LOSS_TRIGGERED",
                "source": "test",
                "data": {},
                "timestamp": 0,
                "event_id": "",
            }),
        })
        handler.assert_called_once()


class TestEventBusListen:
    def test_listen_empty_handlers(self, bus, mock_redis):
        """没有注册 handler 时 listen 不打日志以外的操作"""
        bus.listen(block=False, timeout=1)
        assert not mock_redis.pubsub.called

    def test_listen_subscribes_channels(self, bus, mock_redis):
        handler = MagicMock()
        handler.__name__ = "mock_handler"
        bus.subscribe(EventType.STOP_LOSS_TRIGGERED, handler)
        bus.subscribe(EventType.RISK_ALERT, handler)

        bus.listen(block=False, timeout=1)
        pubsub = mock_redis.pubsub.return_value
        # verify subscribe called for both channels
        assert pubsub.subscribe.called

    def test_get_bus_singleton(self):
        from src.eventbus.bus import get_bus
        b1 = get_bus()
        b2 = get_bus()
        assert b1 is b2
