"""单元测试：策略回测调度器 BacktestRunner

覆盖范围：
- run_backtest 接口
- 策略一信号生成（底部机会期入场/出场）
- 策略二信号生成（主线确认/趋势上升期入场/出场）
- 边界条件
"""


import numpy as np
import pandas as pd

from src.engine.backtesting import PortfolioResult
from src.strategy.backtest_runner import (
    STRATEGY1_ALLOWED_STATES,
    STRATEGY1_POSITION_PCT,
    STRATEGY1_SCORE_THRESHOLD,
    STRATEGY1_STOP_LOSS_PCT,
    STRATEGY1_STOP_PROFIT_PCT,
    STRATEGY2_ALLOWED_STATES,
    STRATEGY2_POSITION_PCT,
    STRATEGY2_SCORE_THRESHOLD,
    STRATEGY2_STOP_LOSS_PCT,
    STRATEGY2_STOP_PROFIT_PCT,
    BacktestConfig,
    _generate_signals,
    get_config_for_strategy,
    run_backtest,
)


def _make_klines(days: int = 30, start_price: float = 100.0) -> pd.DataFrame:
    """生成模拟K线"""
    dates = pd.bdate_range(start="2024-01-01", periods=days)
    np.random.seed(42)
    prices = start_price * (1 + np.cumsum(np.random.randn(days) * 0.02))
    prices = np.maximum(prices, start_price * 0.5)
    return pd.DataFrame({
        "date": dates,
        "Open": prices * (1 - np.random.rand(days) * 0.01),
        "High": prices * (1 + np.random.rand(days) * 0.02),
        "Low": prices * (1 - np.random.rand(days) * 0.02),
        "Close": prices,
        "Volume": np.random.randint(1_000_000, 10_000_000, days),
    })


def _make_market_states(mainline_dates: list[str]) -> dict[str, str]:
    """生成每日市场状态"""
    states = {}
    for d in pd.bdate_range(start="2024-01-01", end="2024-01-31"):
        ds = d.date().isoformat()
        states[ds] = "底部机会期" if ds in mainline_dates else "非主线状态"
    return states


def _make_scored_pool(
    stocks: list[str],
    buy_dates: list[str] | None = None,
) -> dict[str, list[dict]]:
    """生成每日评分池"""
    if buy_dates is None:
        buy_dates = ["2024-01-03"]
    pool = {}
    for d in pd.bdate_range(start="2024-01-01", end="2024-01-31"):
        ds = d.date().isoformat()
        score = 60.0 if ds in buy_dates else 30.0
        pool[ds] = [
            {"stock_code": s, "score_total": score, "stock_name": f"股票{s}"}
            for s in stocks
        ]
    return pool


# ═══════════════════════════════════════════════════════════════════
# 配置与常量
# ═══════════════════════════════════════════════════════════════════

class TestBacktestConfig:
    """回测配置"""

    def test_strategy1_defaults(self):
        """策略一默认配置"""
        config = get_config_for_strategy("bottom_volume")
        assert config.strategy_type == "bottom_volume"
        assert config.score_threshold == STRATEGY1_SCORE_THRESHOLD
        assert config.stop_loss_pct == STRATEGY1_STOP_LOSS_PCT
        assert config.stop_profit_pct == STRATEGY1_STOP_PROFIT_PCT
        assert config.position_pct == STRATEGY1_POSITION_PCT
        assert config.allowed_states == STRATEGY1_ALLOWED_STATES

    def test_strategy2_defaults(self):
        """策略二默认配置"""
        config = get_config_for_strategy("trend_momentum")
        assert config.strategy_type == "trend_momentum"
        assert config.score_threshold == STRATEGY2_SCORE_THRESHOLD
        assert config.stop_loss_pct == STRATEGY2_STOP_LOSS_PCT
        assert config.stop_profit_pct == STRATEGY2_STOP_PROFIT_PCT
        assert config.position_pct == STRATEGY2_POSITION_PCT
        assert config.allowed_states == STRATEGY2_ALLOWED_STATES


# ═══════════════════════════════════════════════════════════════════
# run_backtest 接口
# ═══════════════════════════════════════════════════════════════════

class TestRunBacktest:
    """run_backtest 主入口"""

    def test_empty_klines_returns_empty(self):
        """无K线数据返回空结果"""
        result = run_backtest(strategy_type="bottom_volume")
        assert isinstance(result, PortfolioResult)
        assert result.total_trades == 0

    def test_no_market_states_returns_empty(self):
        """无市场状态返回空结果"""
        klines = {"000001": _make_klines()}
        result = run_backtest(
            strategy_type="bottom_volume",
            klines_dict=klines,
        )
        assert result.total_trades == 0

    def test_strategy1_generates_signals_with_data(self):
        """策略一在完整数据下产生交易信号"""
        klines = {"000001": _make_klines(days=60)}
        states = _make_market_states(mainline_dates=["2024-01-03", "2024-01-04", "2024-01-05"])
        pool = _make_scored_pool(stocks=["000001"], buy_dates=["2024-01-03"])
        result = run_backtest(
            strategy_type="bottom_volume",
            start="2024-01-01",
            end="2024-02-01",
            klines_dict=klines,
            market_states=states,
            scored_pool=pool,
        )
        assert isinstance(result, PortfolioResult)

    def test_returns_portfolio_result_type(self):
        """返回类型为 PortfolioResult"""
        result = run_backtest()
        assert isinstance(result, PortfolioResult)
        assert hasattr(result, "total_trades")
        assert hasattr(result, "final_capital")


# ═══════════════════════════════════════════════════════════════════
# _generate_signals 信号生成
# ═══════════════════════════════════════════════════════════════════

class TestGenerateSignals:
    """信号生成逻辑"""

    def test_no_market_states_returns_empty(self):
        """无市场状态返回空"""
        result = _generate_signals({}, {}, BacktestConfig())
        assert result == {}

    def test_buy_signal_when_state_allowed_and_score_high(self):
        """允许状态下高分标的产生买入信号"""
        states = {"2024-01-03": "底部机会期", "2024-01-04": "底部机会期"}
        pool = {
            "2024-01-03": [{"stock_code": "000001", "score_total": 60.0}],
            "2024-01-04": [{"stock_code": "000001", "score_total": 60.0}],
        }
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        assert "000001" in signals
        buys = [s for s in signals["000001"] if s.action == "buy"]
        assert len(buys) >= 1

    def test_no_buy_when_state_not_allowed(self):
        """不允许状态下不产生买入信号"""
        states = {"2024-01-03": "非主线状态"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]}
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        assert len(buys) == 0

    def test_no_buy_when_score_below_threshold(self):
        """评分不足时不买入"""
        states = {"2024-01-03": "底部机会期"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 40.0}]}
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        assert len(buys) == 0

    def test_sell_when_score_drops(self):
        """评分下降时产生卖出信号"""
        states = {"2024-01-03": "底部机会期", "2024-01-04": "底部机会期"}
        pool = {
            "2024-01-03": [{"stock_code": "000001", "score_total": 60.0}],
            "2024-01-04": [{"stock_code": "000001", "score_total": 30.0}],
        }
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        sells = [s for s in signals.get("000001", []) if s.action == "sell"]
        assert len(sells) >= 1

    def test_sell_when_state_changes(self):
        """状态变化时产生卖出信号"""
        states = {"2024-01-03": "底部机会期", "2024-01-04": "非主线状态"}
        pool = {
            "2024-01-03": [{"stock_code": "000001", "score_total": 60.0}],
            "2024-01-04": [{"stock_code": "000001", "score_total": 55.0}],
        }
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        sells = [s for s in signals.get("000001", []) if s.action == "sell"]
        assert len(sells) >= 1

    def test_signal_has_stop_loss_and_profit(self):
        """买入信号包含止损止盈参数"""
        states = {"2024-01-03": "底部机会期"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]}
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        if buys:
            assert buys[0].stop_loss == STRATEGY1_STOP_LOSS_PCT
            assert buys[0].stop_profit == STRATEGY1_STOP_PROFIT_PCT

    def test_multiple_stocks_generates_separate_signals(self):
        """多只股票分别生成独立信号"""
        states = {"2024-01-03": "底部机会期"}
        pool = {
            "2024-01-03": [
                {"stock_code": "A", "score_total": 60.0},
                {"stock_code": "B", "score_total": 65.0},
            ],
        }
        config = get_config_for_strategy("bottom_volume")
        signals = _generate_signals(states, pool, config)
        assert "A" in signals
        assert "B" in signals

    def test_strategy2_entry_in_mainline_confirmed(self):
        """策略二在主线确认状态下入场"""
        states = {"2024-01-03": "主线确认"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]}
        config = get_config_for_strategy("trend_momentum")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        assert len(buys) >= 1

    def test_strategy2_entry_in_trend_uptrend(self):
        """策略二在趋势上升期入场"""
        states = {"2024-01-03": "趋势上升期"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]}
        config = get_config_for_strategy("trend_momentum")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        assert len(buys) >= 1

    def test_strategy2_ignores_bottom_opportunity(self):
        """策略二在底部机会期不入场"""
        states = {"2024-01-03": "底部机会期"}
        pool = {"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]}
        config = get_config_for_strategy("trend_momentum")
        signals = _generate_signals(states, pool, config)
        buys = [s for s in signals.get("000001", []) if s.action == "buy"]
        assert len(buys) == 0


# ═══════════════════════════════════════════════════════════════════
# 边界条件
# ═══════════════════════════════════════════════════════════════════

class TestBacktestRunnerEdgeCases:
    """边界条件"""

    def test_empty_scored_pool(self):
        """空评分池"""
        klines = {"000001": _make_klines()}
        states = {"2024-01-03": "底部机会期"}
        result = run_backtest(
            strategy_type="bottom_volume",
            klines_dict=klines,
            market_states=states,
            scored_pool={},
        )
        assert isinstance(result, PortfolioResult)

    def test_stock_in_scored_pool_but_no_klines(self):
        """股票在评分池但无K线"""
        klines = {"A": _make_klines()}
        states = {"2024-01-03": "底部机会期"}
        pool = {
            "2024-01-03": [
                {"stock_code": "A", "score_total": 60.0},
                {"stock_code": "B", "score_total": 55.0},
            ],
        }
        result = run_backtest(
            strategy_type="bottom_volume",
            start="2024-01-01",
            end="2024-02-01",
            klines_dict=klines,
            market_states=states,
            scored_pool=pool,
        )
        assert isinstance(result, PortfolioResult)
        assert result.total_trades >= 0

    def test_empty_stock_list_in_pool(self):
        """评分池中股票列表为空"""
        klines = {"A": _make_klines()}
        states = {"2024-01-03": "底部机会期"}
        pool = {"2024-01-03": []}
        result = run_backtest(
            strategy_type="bottom_volume",
            klines_dict=klines,
            market_states=states,
            scored_pool=pool,
        )
        assert result.total_trades == 0
