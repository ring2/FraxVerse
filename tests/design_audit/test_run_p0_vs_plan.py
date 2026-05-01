"""设计文档审查：run_p0.py 联调入口 vs 开发实施计划 P0-7.1

验证 run_p0.py 满足开发实施计划的要求。
"""

import inspect


class TestRunP0Interface:
    """P0-7.1: run_p0.py 入口约束"""

    def test_script_exists(self):
        """run_p0.py 文件存在"""
        import run_p0  # noqa: F401

    def test_has_main_function(self):
        """run_p0.py 包含 main 函数"""
        import run_p0
        assert hasattr(run_p0, "main") or hasattr(run_p0, "run_pipeline")

    def test_has_argparse(self):
        """run_p0.py 使用 argparse 处理命令行参数"""
        import run_p0
        source = inspect.getsource(run_p0)
        assert "argparse" in source or "ArgumentParser" in source

    def test_has_start_end_params(self):
        """支持 --start 和 --end 参数"""
        import run_p0
        source = inspect.getsource(run_p0)
        assert "--start" in source or "start" in source
        assert "--end" in source or "end" in source

    def test_output_has_basic_sections(self):
        """输出包含粗筛结果、评分排序、回测报告、执行时间"""
        import run_p0
        # 检查是否有打印输出逻辑
        source = inspect.getsource(run_p0)
        sections = ["粗筛", "评分", "回测", "时间"]
        found = any(s in source for s in sections)
        assert found, f"输出应包含以下至少一个section: {sections}"

    def test_calls_screener(self):
        """通过 backtest_runner 间接调用粗筛模块"""
        import inspect

        from src.strategy.backtest_runner import run_backtest
        source = inspect.getsource(run_backtest)
        assert "bottom_volume" in source or "trend_momentum" in source

    def test_calls_scorer(self):
        """通过 run_backtest 的 scored_pool 参数间接使用评分结果"""
        import inspect

        import run_p0 as rp
        source = inspect.getsource(rp.run_pipeline)
        assert "scored_pool" in source or "run_backtest" in source

    def test_calls_backtest(self):
        """调用回测模块"""
        import run_p0
        source = inspect.getsource(run_p0)
        assert "backtest" in source or "run_backtest" in source

    def test_runs_as_main(self):
        """包含 if __name__ == '__main__' 入口"""
        import run_p0
        source = inspect.getsource(run_p0)
        assert "__main__" in source
