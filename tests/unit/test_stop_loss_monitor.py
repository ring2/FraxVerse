"""
P1-2.2 止损监视器 — 单元测试
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.db.models import (
    Base,
    DailyKlines,
    Positions,
    RiskEvents,
    Stocks,
    StopLossConditions,
    TradeMode,
)
from src.monitor.stop_loss import StopLossMonitor

TEST_DB_URL = "postgresql://fraxverse:fraxverse_dev@localhost:5432/fraxverse_test"


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    session.commit()
    session.close()


@pytest.fixture
def seed_basic(db_session):
    stock = Stocks(code="600519.SH", name="贵州茅台", market="SH")
    db_session.add(stock)
    trade_mode = TradeMode(
        current_mode="SIMULATION", confirm_mode="advisory",
        emergency_stop=False,
    )
    db_session.add(trade_mode)
    db_session.commit()
    return stock


@pytest.fixture
def seed_position(db_session, seed_basic):
    pos = Positions(
        stock_code="600519.SH",
        total_volume=1000,
        available_volume=1000,
        cost_price=Decimal("100.00"),
        market_value=Decimal("100000"),
        unrealized_pnl=Decimal("0"),
        unrealized_pnl_pct=Decimal("0"),
        position_pct=Decimal("10"),
        batch_stage="first",
    )
    db_session.add(pos)
    db_session.flush()
    return pos


@pytest.fixture
def seed_stop_loss(db_session, seed_position):
    sl = StopLossConditions(
        position_id=seed_position.id,
        stock_code="600519.SH",
        condition_type="fixed",
        stop_loss_price=Decimal("95.00"),
        max_loss_pct=Decimal("5.00"),
        max_loss_amount=Decimal("5000"),
        is_active=True,
    )
    db_session.add(sl)
    db_session.flush()
    return sl


def add_kline(db_session, price):
    kline = DailyKlines(
        stock_code="600519.SH",
        trade_date=date.today(),
        open=price, high=price, low=price, close=price,
        volume=100000, amount=price * 100000,
    )
    db_session.add(kline)
    db_session.flush()
    return kline


class TestStopLossMonitor:

    @patch("src.monitor.stop_loss.get_session")
    def test_no_positions_skip(self, mock_get_session, db_session, seed_basic):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()

    @patch("src.monitor.stop_loss.get_session")
    def test_no_stop_loss_condition_skip(self, mock_get_session, db_session, seed_position):
        add_kline(db_session, Decimal("100"))
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()

    @patch("src.monitor.stop_loss.get_session")
    def test_fixed_stop_loss_not_triggered(self, mock_get_session, db_session, seed_position, seed_stop_loss):
        add_kline(db_session, Decimal("96"))
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()
        assert len(db_session.query(RiskEvents).all()) == 0

    @patch("src.monitor.stop_loss.get_session")
    @patch("src.monitor.stop_loss.TradeEngine")
    def test_fixed_stop_loss_triggered(self, MockEngine, mock_get_session, db_session, seed_position, seed_stop_loss):
        add_kline(db_session, Decimal("94"))
        mock_order = MagicMock(id=999)
        MockEngine.return_value.sell.return_value = mock_order
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()
        MockEngine.return_value.sell.assert_called_once()

    @patch("src.monitor.stop_loss.get_session")
    @patch("src.monitor.stop_loss.TradeEngine")
    def test_max_loss_pct_triggered(self, MockEngine, mock_get_session, db_session, seed_position):
        sl = StopLossConditions(
            position_id=seed_position.id, stock_code="600519.SH",
            condition_type="percentage", stop_loss_price=Decimal("0.01"),
            max_loss_pct=Decimal("3.00"), is_active=True,
        )
        db_session.add(sl)
        db_session.flush()
        add_kline(db_session, Decimal("96"))
        mock_order = MagicMock(id=888)
        MockEngine.return_value.sell.return_value = mock_order
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()
        MockEngine.return_value.sell.assert_called_once()

    @patch("src.monitor.stop_loss.get_session")
    @patch("src.monitor.stop_loss.TradeEngine")
    def test_max_loss_amount_triggered(self, MockEngine, mock_get_session, db_session, seed_position):
        sl = StopLossConditions(
            position_id=seed_position.id, stock_code="600519.SH",
            condition_type="amount", stop_loss_price=Decimal("0.01"),
            max_loss_pct=Decimal("99.00"), max_loss_amount=Decimal("3000"),
            is_active=True,
        )
        db_session.add(sl)
        db_session.flush()
        add_kline(db_session, Decimal("97"))
        mock_order = MagicMock(id=777)
        MockEngine.return_value.sell.return_value = mock_order
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()
        MockEngine.return_value.sell.assert_called_once()

    @patch("src.monitor.stop_loss.get_session")
    def test_emergency_stop_skip(self, mock_get_session, db_session, seed_position, seed_stop_loss):
        db_session.query(TradeMode).first().emergency_stop = True
        db_session.commit()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        StopLossMonitor()._scan_cycle()

    @patch("src.monitor.stop_loss.get_session")
    def test_zero_available_volume_skip(self, mock_get_session, db_session, seed_position, seed_stop_loss):
        seed_position.available_volume = 0
        db_session.commit()
        add_kline(db_session, Decimal("90"))
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        with patch("src.monitor.stop_loss.TradeEngine") as MockEngine:
            StopLossMonitor()._scan_cycle()
            MockEngine.return_value.sell.assert_not_called()

    @patch("src.monitor.stop_loss.get_session")
    def test_check_single(self, mock_get_session, db_session, seed_position, seed_stop_loss):
        add_kline(db_session, Decimal("98"))
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = StopLossMonitor().check_single(seed_position.id)
        assert result["stock_code"] == "600519.SH"
        assert result["current_price"] == 98.0
        assert result["cost_price"] == 100.0
        assert result["pnl_pct"] == pytest.approx(-2.0)
        assert result["stop_loss_price"] == 95.0
        assert result["max_loss_pct"] == 5.0

    @patch("src.monitor.stop_loss.get_session")
    def test_check_single_no_position(self, mock_get_session, db_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        result = StopLossMonitor().check_single(99999)
        assert "error" in result

    def test_start_stop(self):
        monitor = StopLossMonitor(scan_interval=1)
        assert monitor._running is False
        monitor.stop()


class TestStopLossDesignAudit:
    """P1-2.2 设计审查"""

    def test_monitor_has_scan_cycle(self):
        assert hasattr(StopLossMonitor(), "_scan_cycle")

    def test_monitor_has_check_position(self):
        assert hasattr(StopLossMonitor(), "_check_position")

    def test_monitor_has_execute_stop_loss(self):
        assert hasattr(StopLossMonitor(), "_execute_stop_loss")

    def test_monitor_has_check_single(self):
        assert hasattr(StopLossMonitor(), "check_single")

    def test_monitor_has_signal_handling(self):
        assert hasattr(StopLossMonitor(), "_handle_signal")

    def test_stop_loss_conditions_model_exists(self):
        assert StopLossConditions.__tablename__ == "stop_loss_conditions"

    def test_stop_loss_conditions_has_required_fields(self):
        columns = [c.name for c in StopLossConditions.__table__.columns]
        for field in ["position_id", "stock_code", "condition_type", "stop_loss_price", "max_loss_pct", "max_loss_amount", "is_active"]:
            assert field in columns

    def test_risk_events_model_exists(self):
        assert RiskEvents.__tablename__ == "risk_events"

    def test_run_monitor_function_exists(self):
        from src.monitor.stop_loss import run_monitor
        assert callable(run_monitor)

    def test_default_scan_interval(self):
        assert StopLossMonitor().scan_interval == 30
