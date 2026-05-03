"""FraxVerse Alembic 迁移配置

从 src.db.models 自动发现所有模型表（26 张表），
支持自动生成迁移脚本（autogenerate）。

用法：
  alembic revision --autogenerate -m "描述变更"
  alembic upgrade head
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── 导入所有模型以填充 metadata ──────────────────────────────────
from src.db.session import Base
from src.db.models import (
    Users,
    Sessions,
    SystemConfig,
    Stocks,
    DailyKlines,
    News,
    SectorData,
    TradeOrders,
    Positions,
    TradeMode,
    MarketStateLog,
    StockPool,
    StrategyParams,
    BacktestResults,
    AgentDiscussions,
    AgentWeights,
    Notifications,
    RiskEvents,
    RiskMetricsDaily,
    Experiences,
    AccountSyncLog,
    StopProfitConditions,
    StopLossConditions,
    AgentDecision,
    LlmUsage,
    AgentPrompt,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL 脚本，不连接数据库"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
