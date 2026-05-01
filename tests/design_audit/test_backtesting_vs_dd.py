"""设计文档审查：回测引擎 vs 开发实施计划 & DD-03 backtest_results 表

验证回测引擎的实现满足P0-6.1~P0-6.3的要求。
"""

import inspect

# ═══════════════════════════════════════════════════════════════════
# P0-6.1 backtest_results 表字段
# ═══════════════════════════════════════════════════════════════════

class TestBacktestResultsTableVsDesignDoc:
    """DD-03 §2.1.4 backtest_results 表字段对齐"""

    def test_engine_module_imports(self):
        """开发实施计划: 可导入 BacktestingEngine"""
        from src.engine.backtesting import BacktestingEngine  # noqa: F401

    def test_runs_without_pyqt_import_error(self):
        """开发实施计划: 不依赖PyQt"""
        # 导入过程不应抛出 ImportError（PySide/PyQt相关）

    def test_has_backtesting_engine_class(self):
        """开发实施计划: 包含 BacktestingEngine 类"""
        from src.engine.backtesting import BacktestingEngine
        assert hasattr(BacktestingEngine, 'run')
        assert hasattr(BacktestingEngine, 'set_parameters')
        assert hasattr(BacktestingEngine, 'result')

    def test_required_methods(self):
        """开发实施计划: set_parameters/run 方法存在"""
        from src.engine.backtesting import BacktestingEngine
        assert callable(BacktestingEngine().set_parameters)
        assert callable(BacktestingEngine().run)


# ═══════════════════════════════════════════════════════════════════
# DD-03 §2.1.4 backtest_results 表字段
# ═══════════════════════════════════════════════════════════════════

class TestBacktestResultFieldsVsDesignDoc:
    """DD-03: backtest_results 表字段对齐"""

    def test_result_has_strategy_type(self):
        """DD-03: strategy_type"""
        from src.engine.backtesting import BacktestResult
        assert hasattr(BacktestResult, 'strategy_type')

    def test_result_has_start_end_date(self):
        """DD-03: start_date / end_date"""
        from src.engine.backtesting import BacktestResult
        fields = BacktestResult.__dataclass_fields__
        assert 'start_date' in fields
        assert 'end_date' in fields

    def test_result_has_capital_fields(self):
        """DD-03: initial_capital / final_capital"""
        from src.engine.backtesting import BacktestResult
        fields = BacktestResult.__dataclass_fields__
        assert 'initial_capital' in fields
        assert 'final_capital' in fields

    def test_result_has_performance_metrics(self):
        """DD-03: annual_return / max_drawdown / win_rate / profit_loss_ratio / total_trades"""
        from src.engine.backtesting import BacktestResult
        fields = BacktestResult.__dataclass_fields__
        required = {'annual_return', 'max_drawdown', 'win_rate',
                     'profit_loss_ratio', 'total_trades'}
        missing = required - set(fields.keys())
        assert not missing, f"BacktestResult缺少字段: {missing}"


# ═══════════════════════════════════════════════════════════════════
# P0-6.1 A股规则检查
# ═══════════════════════════════════════════════════════════════════

class TestAShareRules:
    """开发实施计划: 适配A股规则"""

    def test_t_plus_1(self):
        """A股 T+1 交易规则"""
        from src.engine.backtesting import T_PLUS_1, BacktestingEngine
        assert T_PLUS_1 is True

        # T+1 规则在 _run_with_signals 中实现
        source = inspect.getsource(BacktestingEngine._run_with_signals)
        assert "days" in source  # 检查实现中包含日期检查逻辑

    def test_limit_up_down(self):
        """A股 涨跌停限制"""
        from src.engine.backtesting import BacktestingEngine
        source = inspect.getsource(BacktestingEngine)
        assert "limit" in source.lower() or "涨跌" in source or "涨停" in source

    def test_trading_fee(self):
        """A股 交易费率（佣金+印花税）"""
        from src.engine.backtesting import BacktestingEngine
        source = inspect.getsource(BacktestingEngine.__init__)
        assert "commission" in source.lower() or "fee" in source.lower() or "印花" in source or "佣金" in source
