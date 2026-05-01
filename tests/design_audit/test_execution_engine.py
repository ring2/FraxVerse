"""
设计审查：交易执行模块 vs DD-05 设计文档
"""
from pathlib import Path

SRC_DIR = Path("/home/ubuntu/FraxVerse/src/execution")


def test_engine_module_exists():
    """engine.py 应存在"""
    assert (SRC_DIR / "engine.py").exists()


def test_order_executor_class_exists():
    """应有 OrderExecutor 类"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "class OrderExecutor" in content


def test_position_manager_class_exists():
    """应有 PositionManager 类"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "class PositionManager" in content


def test_stop_profit_manager_class_exists():
    """应有 StopProfitManager 类"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "class StopProfitManager" in content


def test_trade_engine_class_exists():
    """应有 TradeEngine 类"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "class TradeEngine" in content


def test_trade_error_classes():
    """应有完整的错误类层次"""
    content = (SRC_DIR / "engine.py").read_text()
    errors = ["TradeError", "NoStockError", "StopLossNotBoundError",
              "FlatAverageForbiddenError", "RiskLimitError",
              "CooldownError", "EmergencyStopError", "DuplicateOrderError"]
    for err in errors:
        assert f"class {err}" in content, f"缺少 {err} 异常类"


def test_execute_order_has_validation_flow():
    """execute_order 应包含校验流程"""
    content = (SRC_DIR / "engine.py").read_text()
    steps = ["_check_emergency_stop", "_load_stock", "_check_cooldown",
             "_check_flat_average_ban", "_check_risk_limit"]
    for step in steps:
        assert step in content, f"execute_order 缺少 {step}"


def test_batch_position_constants():
    """应有推进式仓位常量"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "BATCH_FIRST_PCT" in content
    assert "BATCH_SECOND_PCT" in content
    assert "BATCH_REMAINDER_PCT" in content


def test_max_positions_constant():
    """应有最大持仓数常量"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "MAX_POSITIONS" in content


def test_stop_profit_tiers():
    """应有阶梯止盈配置"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "STOP_PROFIT_TIERS" in content
    assert "first_take" in content
    assert "second_take" in content
    assert "trailing" in content


def test_buy_sell_close_methods():
    """TradeEngine 应有 buy/sell/close_all 方法"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "def buy(" in content
    assert "def sell(" in content
    assert "def close_all(" in content


def test_mode_upgrade_paths():
    """应有模式升级路径常量"""
    content = (SRC_DIR / "engine.py").read_text()
    assert "CONFIRM_MODE_UPGRADE_PATH" in content
    assert "TRADE_MODE_UPGRADE_PATH" in content
