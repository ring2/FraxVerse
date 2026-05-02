"""
P1-2.3 微信推送服务 — 单元测试
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, Notifications, Users
from src.notification.wechat import (
    NotificationPriority,
    NotificationType,
    WeChatNotifier,
    get_notifier,
)

TEST_DB_URL = "postgresql://fraxverse:fraxverse_dev@localhost:5432/fraxverse_test"


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_notifications(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    session.execute(text('DELETE FROM notifications'))
    session.commit()
    session.close()


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def seed_user(db_session):
    user = Users(
        username="test_user_" + str(uuid.uuid4())[:8],
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def notifier(seed_user):
    return WeChatNotifier(user_id=seed_user.id)


class TestWeChatNotifier:

    @patch("src.notification.wechat.get_session")
    def test_send_basic(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send(
            event_type=NotificationType.TRADE_SIGNAL,
            title="测试通知",
            content="测试内容",
        )
        assert result is not None
        assert result.event_type == "trade_signal"
        assert result.push_status == "sent"

    @patch("src.notification.wechat.get_session")
    def test_send_dedup(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        key = "dedup_" + str(uuid.uuid4())[:8]
        result1 = notifier.send(
            event_type=NotificationType.TRADE_SIGNAL,
            title="去重测试",
            content="内容",
            dedup_key=key,
        )
        assert result1 is not None
        result2 = notifier.send(
            event_type=NotificationType.TRADE_SIGNAL,
            title="去重测试",
            content="内容",
            dedup_key=key,
        )
        assert result2 is None

    @patch("src.notification.wechat.get_session")
    def test_send_trade_signal(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send_trade_signal(
            stock_code="600519.SH",
            action="buy",
            price=Decimal("100.50"),
            quantity=100,
            reason="突破买入",
        )
        assert result is not None
        assert result.event_type == "trade_signal"
        assert "600519.SH" in result.title
        assert result.priority == "high"

    @patch("src.notification.wechat.get_session")
    def test_send_stop_loss_alert(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send_stop_loss_alert(
            stock_code="000001.SZ",
            trigger_price=Decimal("95"),
            cost_price=Decimal("100"),
            pnl_pct=Decimal("-5"),
            reason="跌破止损价",
        )
        assert result is not None
        assert result.event_type == "stop_loss"
        assert result.priority == "urgent"

    @patch("src.notification.wechat.get_session")
    def test_send_stop_profit_alert(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send_stop_profit_alert(
            stock_code="600519.SH",
            current_price=Decimal("150"),
            cost_price=Decimal("100"),
            pnl_pct=Decimal("50"),
            stage="first_take",
        )
        assert result is not None
        assert result.event_type == "stop_profit"
        assert result.priority == "high"

    @patch("src.notification.wechat.get_session")
    def test_send_risk_warning(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send_risk_warning(
            title="回撤超限",
            content="当日回撤超过3%",
            risk_data={"drawdown": 3.5},
        )
        assert result is not None
        assert result.event_type == "risk_warning"
        assert result.priority == "high"

    @patch("src.notification.wechat.get_session")
    def test_send_system_error(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = notifier.send_system_error(
            error_msg="数据库连接失败",
            module="db_engine",
        )
        assert result is not None
        assert result.event_type == "system_error"
        assert result.priority == "urgent"

    @patch("src.notification.wechat.get_session")
    def test_send_daily_report(self, mock_get_session, db_session, notifier, seed_user):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        report = {
            "total_asset": 100000,
            "daily_pnl": 1500,
            "position_count": 3,
            "trade_count": 2,
        }
        result = notifier.send_daily_report(report)
        assert result is not None
        assert result.event_type == "daily_report"
        assert result.priority == "normal"

    def test_get_notifier(self):
        notifier = get_notifier()
        assert isinstance(notifier, WeChatNotifier)
        assert notifier.user_id == 1

    def test_notification_types(self):
        assert NotificationType.TRADE_SIGNAL == "trade_signal"
        assert NotificationType.STOP_LOSS == "stop_loss"
        assert NotificationType.DAILY_REPORT == "daily_report"

    def test_priority_levels(self):
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.URGENT == "urgent"


class TestWeChatDesignAudit:
    """P1-2.3 设计审查"""

    def test_notifier_class_exists(self):
        assert WeChatNotifier is not None

    def test_notifier_has_send_method(self):
        notifier = WeChatNotifier()
        assert hasattr(notifier, "send")
        assert callable(notifier.send)

    def test_notifier_has_convenience_methods(self):
        notifier = WeChatNotifier()
        methods = [
            "send_trade_signal",
            "send_stop_loss_alert",
            "send_stop_profit_alert",
            "send_risk_warning",
            "send_system_error",
            "send_daily_report",
        ]
        for method in methods:
            assert hasattr(notifier, method), f"缺少方法: {method}"

    def test_notifications_model_exists(self):
        assert Notifications.__tablename__ == "notifications"

    def test_notifications_has_required_fields(self):
        columns = [c.name for c in Notifications.__table__.columns]
        required = [
            "user_id", "event_type", "priority", "title", "content",
            "push_channel", "push_status", "dedup_key", "retry_count",
        ]
        for field in required:
            assert field in columns, f"缺少字段: {field}"

    def test_dedup_key_support(self):
        notifier = WeChatNotifier()
        import inspect
        sig = inspect.signature(notifier.send)
        assert "dedup_key" in sig.parameters
