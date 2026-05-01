"""边界条件测试：P0全流程在各种异常情况下的健壮性

覆盖场景（P0-7.2）：
- 数据源不可用 → 优雅降级
- 候选池为空 → 提示"今日无符合条件的标的"
- 数据格式异常 → 不崩溃，记录错误日志
- 回测区间无数据 → 输出空报告
"""

import pytest

from src.engine.backtesting import BacktestResult, PortfolioResult
from src.strategy.backtest_runner import get_config_for_strategy, run_backtest


class TestEmptyCandidatePool:
    """候选池为空的场景"""

    def test_run_backtest_empty_pool(self):
        """策略一空候选池返回空结果"""
        states = {"2024-01-03": "底部机会期"}
        result = run_backtest(
            strategy_type="bottom_volume",
            market_states=states,
            scored_pool={},
        )
        assert isinstance(result, PortfolioResult)
        assert result.total_trades == 0
        assert result.final_capital == result.initial_capital

    def test_run_backtest_no_stock_meets_threshold(self):
        """所有标的评分不足阈值"""
        states = {"2024-01-03": "底部机会期"}
        pool = {"2024-01-03": [{"stock_code": "A", "score_total": 30.0}]}
        result = run_backtest(
            strategy_type="bottom_volume",
            market_states=states,
            scored_pool=pool,
        )
        assert result.total_trades == 0


class TestNoDataGracefulDegradation:
    """数据不可用的优雅降级"""

    def test_empty_klines_returns_empty(self):
        """无K线数据返回空结果"""
        result = run_backtest(strategy_type="bottom_volume")
        assert isinstance(result, PortfolioResult)
        assert result.total_trades == 0

    def test_none_entries_handled(self):
        """None作为参数不崩溃"""
        result = run_backtest(
            strategy_type=None,
            start=None,
            end=None,
        )
        assert isinstance(result, PortfolioResult)

    def test_partial_date_range_handled(self):
        """只有start没有end"""
        result = run_backtest(strategy_type="bottom_volume", start="2024-01-01")
        assert isinstance(result, PortfolioResult)

    def test_capital_zero_no_crash(self):
        """资金为0不崩溃"""
        result = run_backtest(
            strategy_type="bottom_volume",
            capital=0,
        )
        assert result.final_capital == 0


class TestMalformedData:
    """数据格式异常"""

    def test_malformed_klines_columns(self):
        """缺少必要列的K线报ValueError"""
        import pandas as pd
        klines = {"000001": pd.DataFrame({"a": [1], "b": [2]})}
        with pytest.raises(ValueError, match="缺少必要列"):
            run_backtest(
                strategy_type="bottom_volume",
                start="2024-01-01",
                end="2024-01-10",
                klines_dict=klines,
                market_states={"2024-01-03": "底部机会期"},
                scored_pool={"2024-01-03": [{"stock_code": "000001", "score_total": 60.0}]},
            )

    def test_backtest_result_empty(self):
        """空BacktestResult的数据结构完整"""
        r = BacktestResult()
        d = r.to_insert_dict()
        assert "strategy_type" in d
        assert "total_trades" in d

    def test_portfolio_result_empty(self):
        """空PortfolioResult的数据结构完整"""
        r = PortfolioResult()
        assert r.total_trades == 0
        assert r.final_capital == 0


class TestBacktestRangeNoData:
    """回测区间无数据"""

    def test_future_dates_return_empty(self):
        """未来日期没有数据"""
        result = run_backtest(
            strategy_type="bottom_volume",
            start="2099-01-01",
            end="2099-12-31",
        )
        assert result.total_trades == 0

    def test_backwards_date_range(self):
        """开始日期>结束日期"""
        result = run_backtest(
            strategy_type="bottom_volume",
            start="2024-12-31",
            end="2024-01-01",
        )
        assert isinstance(result, PortfolioResult)

    def test_single_day_range(self):
        """单日区间"""
        result = run_backtest(
            strategy_type="bottom_volume",
            start="2024-01-01",
            end="2024-01-01",
        )
        assert isinstance(result, PortfolioResult)


class TestConfigEdgeCases:
    """配置边界"""

    def test_unknown_strategy_uses_default(self):
        """未知策略类型使用默认配置"""
        config = get_config_for_strategy("unknown_strategy")
        assert config.strategy_type == "bottom_volume"
        assert config.score_threshold > 0
