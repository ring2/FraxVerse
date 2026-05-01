"""
单元测试：交易执行引擎（SIMULATION模式）
测试 TradeEngine, OrderExecutor, PositionManager, StopProfitManager
"""
from decimal import Decimal

import pytest

from src.db.models import (
    Positions,
)
from src.db.models import (
    TradeMode as TradeModeModel,
)
from src.db.session import get_session
from src.execution.engine import (
    CooldownError,
    EmergencyStopError,
    FlatAverageForbiddenError,
    NoStockError,
    OrderExecutor,
    PositionManager,
    RiskLimitError,
    StopProfitManager,
    TradeEngine,
    TradeError,
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db():
    """提供数据库会话（测试后回滚）"""
    session = get_session()
    yield session
    session.rollback()


@pytest.fixture
def seed_stock(db):
    """插入测试用股票数据"""
    from src.db.models import Stocks
    stock = Stocks(code="000001.SZ", name="测试股票", market="SZ")
    db.merge(stock)
    from src.db.models import Positions as PosModel
    db.query(PosModel).filter_by(stock_code="000001.SZ").delete()
    db.commit()


@pytest.fixture
def te(db, seed_stock):
    """提供交易引擎实例"""
    return TradeEngine(db)


# ============================================================================
# 下单执行器测试
# ============================================================================

class TestOrderExecutor:
    """OrderExecutor 完整下单校验流程"""

    def test_execute_order_buy_simulation(self, db, seed_stock):
        """SIMULATION模式下买入应直接标记成交"""
        executor = OrderExecutor(db)
        order = executor.execute_order(
            stock_code="000001.SZ",
            direction="buy",
            volume=100,
            price=Decimal("10"),
            strategy_type="bottom_volume",
            trigger_source="strategy",
            reason="策略一测试",
        )
        assert order.status == "filled"
        assert order.direction == "buy"
        assert order.filled_volume == 100
        assert order.trade_mode == "SIMULATION"


    def test_execute_order_sell_simulation(self, db, seed_stock):
        """SIMULATION模式下卖出"""
        executor = OrderExecutor(db)
        order = executor.execute_order(
            stock_code="000001.SZ",
            direction="sell",
            volume=100,
            price=Decimal("12"),
            reason="止盈卖出",
        )
        assert order.status == "filled"
        assert order.direction == "sell"


    def test_no_stock_raises_error(self, db):
        """不存在的股票应抛 NoStockError"""
        executor = OrderExecutor(db)
        with pytest.raises(NoStockError):
            executor.execute_order(
                stock_code="999999.XX",
                direction="buy",
                volume=100,
            )


# ============================================================================
# 仓位管理器测试
# ============================================================================

class TestPositionManager:

    def test_get_positions_empty(self, db):
        """初始状态持仓应为空"""
        pm = PositionManager(db)
        positions = pm.get_positions()
        assert isinstance(positions, list)


    def test_can_open_new_position(self, db):
        """默认应能开新仓"""
        pm = PositionManager(db)
        assert pm.can_open_new_position() is True


    def test_calculate_batch_quantity_first_half(self, db):
        """第一批计算应返回合理值"""
        pm = PositionManager(db, total_asset=Decimal("100000"))
        qty = pm.calculate_batch_quantity("600519.SH", Decimal("100"), "first_half")
        assert qty >= 100
        assert qty % 100 == 0


# ============================================================================
# 止盈管理器测试
# ============================================================================

class TestStopProfitManager:

    def test_create_stop_profit(self, db, seed_stock):
        """创建止盈应返回3个阶梯条件"""
        spm = StopProfitManager(db)
        pos = Positions(stock_code="000001.SZ", total_volume=100, cost_price=Decimal("10"))
        db.add(pos)
        db.flush()

        conditions = spm.create_stop_profit(pos.id, "000001.SZ")
        assert len(conditions) == 3
        stages = {c.stage for c in conditions}
        assert "first_take" in stages
        assert "second_take" in stages
        assert "trailing" in stages


    def test_check_stop_profit_not_triggered(self, db, seed_stock):
        """涨幅不足不应触发止盈"""
        spm = StopProfitManager(db)
        pos = Positions(stock_code="000001.SZ", total_volume=100, cost_price=Decimal("10"))
        db.add(pos)
        db.flush()
        spm.create_stop_profit(pos.id, "000001.SZ")

        result = spm.check_and_execute("000001.SZ", Decimal("10.5"), Decimal("10"))
        assert result is None


    def test_check_stop_profit_first_take(self, db, seed_stock):
        """涨幅10%应触发第一批止盈"""
        spm = StopProfitManager(db)
        pos = Positions(stock_code="000001.SZ", total_volume=100, cost_price=Decimal("10"))
        db.add(pos)
        db.flush()
        spm.create_stop_profit(pos.id, "000001.SZ")

        result = spm.check_and_execute("000001.SZ", Decimal("11"), Decimal("10"))
        assert result == Decimal("30")


# ============================================================================
# 交易引擎集成测试
# ============================================================================

class TestTradeEngine:

    def test_buy_via_engine(self, db, te):
        """TradeEngine.buy 应返回已成交订单"""
        order = te.buy(stock_code="000001.SZ", volume=100, price=Decimal("10"), strategy_type="bottom_volume")
        assert order is not None
        assert order.status == "filled"
        assert order.strategy_type == "bottom_volume"


    def test_sell_via_engine(self, db, te):
        """TradeEngine.sell 应返回已成交订单"""
        order = te.sell(stock_code="000001.SZ", volume=100, price=Decimal("12"))
        assert order.status == "filled"


    def test_close_all_empty(self, db, te):
        """无持仓时 close_all 应返回空列表"""
        orders = te.close_all()
        assert len(orders) == 0


    def test_set_cooldown(self, db, te):
        """设置冷却期"""
        pos = Positions(stock_code="000001.SZ", total_volume=100, cost_price=Decimal("10"))
        db.add(pos)
        db.flush()

        updated = te.set_cooldown("000001.SZ", "stop_loss")
        assert updated.is_cooling_down is True
        assert updated.cool_down_reason == "stop_loss"


# ============================================================================
# 紧急停止测试（最后执行，使用独立会话）
# ============================================================================

class TestEmergencyStop:

    def test_emergency_stop_blocks_order(self):
        """紧急停止应阻止下单"""
        session = get_session()
        try:
            mode = session.query(TradeModeModel).first()
            mode.emergency_stop = True
            session.commit()

            executor = OrderExecutor(session)
            with pytest.raises(EmergencyStopError):
                executor.execute_order(
                    stock_code="000001.SZ",
                    direction="buy",
                    volume=10,
                    price=Decimal("10"),
                )
        finally:
            mode = session.query(TradeModeModel).first()
            mode.emergency_stop = False
            session.commit()
            session.close()


# ============================================================================
# 错误处理测试
# ============================================================================

class TestTradeErrors:

    def test_trade_error_hierarchy(self):
        """测试错误类层次结构"""
        assert issubclass(NoStockError, TradeError)
        assert issubclass(CooldownError, TradeError)
        assert issubclass(FlatAverageForbiddenError, TradeError)
        assert issubclass(RiskLimitError, TradeError)
        assert issubclass(EmergencyStopError, TradeError)


    def test_trade_error_code_and_http(self):
        """错误应有code和http_status"""
        err = NoStockError("股票不存在")
        assert err.code == "40401"
        assert err.http_status == 400
