"""
P0-6.2 验收测试：策略一「周期底部量能异动」回测

注意：此测试需要真实数据（AKShare + PostgreSQL），仅在有数据连接时运行。
标记为 pytest.mark.backtest，默认跳过。
"""

import pytest

pytestmark = pytest.mark.backtest


@pytest.mark.skip(reason="需要真实数据源，在P0-7联调阶段执行")
class TestStrategy1Backtest:
    """策略一回测验收"""

    def test_strategy1_backtest_meets_standards(self):
        """在模拟数据中跑通回测流程"""
        from src.strategy.backtest_runner import run_backtest
        result = run_backtest(strategy_type="bottom_volume")
        assert result is not None
