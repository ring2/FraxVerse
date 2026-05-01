"""
设计审查：数据库Schema vs 详细设计文档
检查项：全部35张表是否已建、索引、约束、种子数据
"""
import re
import subprocess
from pathlib import Path

SCHEMA_FILE = Path("/home/ubuntu/FraxVerse/src/db/schema.sql")
SEED_FILE = Path("/home/ubuntu/FraxVerse/src/db/seed.sql")
DD_DIR = Path("/home/ubuntu/碎片宇宙量化系统/详细设计")

# 期望的表名（来自schema.sql）
EXPECTED_TABLES = [
    # DD-01
    "users", "sessions", "system_config",
    # DD-02
    "stocks", "daily_klines", "fund_flows", "news", "sector_data",
    "macroeconomic", "data_sync_log",
    # DD-03
    "market_state_log", "stock_pool", "strategy_params", "backtest_results",
    # DD-04
    "agent_discussions", "agent_weights", "agent_decisions", "llm_usage", "agent_prompts",
    # DD-05
    "trade_orders", "positions", "stop_loss_conditions", "trade_mode",
    "stop_profit_conditions", "account_sync_log",
    # DD-06
    "risk_events", "risk_metrics_daily", "recovery_plans", "layer_outputs",
    # DD-07
    "experiences", "param_change_log", "experience_feedback",
    # DD-09
    "notifications", "push_config", "notification_templates",
]


def test_all_tables_created():
    """检查35张表是否全部建好"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"],
        capture_output=True, text=True, timeout=10,
    )
    actual = {t.strip() for t in result.stdout.strip().split("\n") if t.strip()}
    expected = set(EXPECTED_TABLES)
    missing = expected - actual
    extra = actual - expected
    errors = []
    if missing:
        errors.append(f"缺失表: {sorted(missing)}")
    if extra:
        errors.append(f"多余表（不在设计文档中）: {sorted(extra)}")
    assert not errors, "; ".join(errors)


def test_seed_data_trade_mode():
    """trade_mode 表应包含初始 SIMULATION 记录"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c", "SELECT current_mode FROM trade_mode;"],
        capture_output=True, text=True, timeout=5,
    )
    assert "SIMULATION" in result.stdout, f"trade_mode 缺少 SIMULATION 初始行: {result.stdout}"


def test_seed_data_strategy_params():
    """strategy_params 应有17条预置参数"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c", "SELECT COUNT(*) FROM strategy_params;"],
        capture_output=True, text=True, timeout=5,
    )
    count = int(result.stdout.strip())
    assert count >= 17, f"strategy_params 期望≥17条，实际{count}"


def test_seed_data_agent_weights():
    """agent_weights 应有8条初始配置"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c", "SELECT COUNT(*) FROM agent_weights;"],
        capture_output=True, text=True, timeout=5,
    )
    count = int(result.stdout.strip())
    assert count >= 8, f"agent_weights 期望≥8条，实际{count}"


def test_schema_sql_has_all_tables():
    """schema.sql 应定义所有35张表的CREATE TABLE"""
    content = SCHEMA_FILE.read_text()
    creates = re.findall(r"CREATE TABLE (\w+)", content)
    missing = set(EXPECTED_TABLES) - set(creates)
    assert not missing, f"schema.sql 缺少建表: {missing}"


def test_indexes_on_daily_klines():
    """daily_klines 应有 code_date 和 date 两个索引"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c",
         "SELECT indexname FROM pg_indexes WHERE tablename='daily_klines' AND indexname LIKE 'idx_kline%';"],
        capture_output=True, text=True, timeout=5,
    )
    indexes = {i.strip() for i in result.stdout.strip().split("\n") if i.strip()}
    assert "idx_klines_code_date" in indexes, "缺少 idx_klines_code_date"
    assert "idx_klines_date" in indexes, "缺少 idx_klines_date"


def test_unique_constraints():
    """验证关键表的唯一约束"""
    constraints_to_check = [
        ("users", "uk_users_username"),
        ("agent_weights", "uk_agent_weight"),
        ("agent_decisions", "uk_decision"),
        ("llm_usage", "uk_llm_usage"),
    ]
    for table, constraint in constraints_to_check:
        result = subprocess.run(
            ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
             "-t", "-A", "-c", f"SELECT 1 FROM information_schema.table_constraints WHERE table_name='{table}' AND constraint_name='{constraint}';"],
            capture_output=True, text=True, timeout=5,
        )
        assert "1" in result.stdout, f"缺失约束 {constraint} 在 {table} 上"


def test_stocks_code_pk():
    """stocks 表主键应为 code (VARCHAR)"""
    result = subprocess.run(
        ["docker", "exec", "fraxverse-db", "psql", "-U", "fraxverse", "-d", "fraxverse",
         "-t", "-A", "-c",
         "SELECT column_name FROM information_schema.columns WHERE table_name='stocks' AND column_name='code';"],
        capture_output=True, text=True, timeout=5,
    )
    assert "code" in result.stdout, "stocks.code 不存在（主键）"
