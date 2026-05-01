"""
FraxVerse · SQLAlchemy ORM 模型（自动反射）

所有35张表自动反射自现有PostgreSQL数据库。
详细的字段定义见 src/db/schema.sql（设计文档DDL）。

用法：
    from src.db.models import Users, Stocks, TradeOrders, ...

特殊模型（手写）：
    - TradeMode: 单行表，提供访问器
"""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base

# ============================================================================
# 常用枚举
# ============================================================================

class TradeModeType(StrEnum):
    SIMULATION = "SIMULATION"
    PAPER = "PAPER"
    LIVE = "LIVE"


class MarketState(StrEnum):
    BOTTOM_OPPORTUNITY = "底部机会期"
    MAINLINE_CONFIRMED = "主线确认"
    TREND_UPTREND = "趋势上升期"
    NO_MAINLINE = "非主线状态"
    WATCH = "观望态"


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    RETRYING = "retrying"


# ============================================================================
# DD-01: 认证与用户模块
# ============================================================================

class Users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    last_login: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("TRUE"))


class Sessions(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    access_jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    refresh_jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    access_expires: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    refresh_expires: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("FALSE"))


class SystemConfig(Base):
    __tablename__ = "system_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'string'"))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


# ============================================================================
# DD-02: 数据管理模块
# ============================================================================

class Stocks(Base):
    __tablename__ = "stocks"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(30))
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    list_date: Mapped[datetime | None] = mapped_column(Date)
    is_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class DailyKlines(Base):
    __tablename__ = "daily_klines"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    adjust_flag: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'none'"))
    ma5: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ma10: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ma20: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ma60: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    adx: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    cmf: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "adjust_flag"),
    )


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_display: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'finance'"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    tags: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'"))
    related_stocks: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'"))
    sentiment: Mapped[str | None] = mapped_column(String(10))
    is_hot: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    hot_score: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    extra: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("url"),
    )


class SectorData(Base):
    __tablename__ = "sector_data"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(20), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sector_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    capital_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    top_volume_stock: Mapped[str | None] = mapped_column(String(10))
    leader_stocks: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'"))
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("sector_code", "trade_date"),
    )


class TradeOrders(Base):
    __tablename__ = "trade_orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_volume: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    filled_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_retry: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    position_batch: Mapped[str | None] = mapped_column(String(20))
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(64))
    strategy_type: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    agent_scores_json: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    stop_profit_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("client_order_id"),
    )


class Positions(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'long'"))
    total_volume: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    available_volume: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default=text("0"))
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default=text("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default=text("0"))
    unrealized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, server_default=text("0"))
    position_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, server_default=text("0"))
    batch_stage: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'none'"))
    first_batch_vol: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    second_batch_vol: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    remainder_vol: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    entry_date: Mapped[datetime | None] = mapped_column(Date)
    last_trade_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_cooling_down: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    cool_down_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cool_down_reason: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("stock_code"),
    )


class TradeMode(Base):
    __tablename__ = "trade_mode"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'SIMULATION'"))
    confirm_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'advisory'"))
    mode_password_hash: Mapped[str | None] = mapped_column(String(255))
    upgraded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    emergency_stop: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    emergency_stopped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class MarketStateLog(Base):
    __tablename__ = "market_state_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    from_state: Mapped[str] = mapped_column(String(16), nullable=False)
    to_state: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    main_line_sector: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class StockPool(Base):
    __tablename__ = "stock_pool"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pass_coarse: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    score_total: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_volume: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_fund: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_sentiment: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_mainforce: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_logic: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    agent_scores: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    final_decision: Mapped[str | None] = mapped_column(String(10))
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    position_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    stop_loss_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    stop_profit_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("date", "stock_code", "strategy_type"),
    )


class StrategyParams(Base):
    __tablename__ = "strategy_params"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    param_key: Mapped[str] = mapped_column(String(50), nullable=False)
    param_value: Mapped[str] = mapped_column(Text, nullable=False)
    param_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'string'"))
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("strategy_type", "param_key"),
    )


class BacktestResults(Base):
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    annual_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    profit_loss_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    total_trades: Mapped[int | None] = mapped_column(Integer)
    params_used: Mapped[dict] = mapped_column(JSONB, nullable=False)
    daily_equity: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class AgentDiscussions(Base):
    __tablename__ = "agent_discussions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    round_num: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    agent_name: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[int | None] = mapped_column(SmallInteger)
    buy_reasons: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    against_reasons: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), server_default=text("0.5"))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    completion_tokens: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    model_name: Mapped[str | None] = mapped_column(String(32))
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    invalid_reason: Mapped[str | None] = mapped_column(String(64))
    predicted_outcome: Mapped[str | None] = mapped_column(String(16))
    actual_outcome: Mapped[str | None] = mapped_column(String(16))
    outcome_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    raw_response: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class AgentWeights(Base):
    __tablename__ = "agent_weights"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(32), nullable=False)
    market_state: Mapped[str] = mapped_column(String(16), nullable=False)
    base_weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    calib_factor: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, server_default=text("1.0"))
    effective_weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), server_default=text("0.5"))
    recent_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    extreme_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    is_degraded: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class Notifications(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'normal'"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    push_channel: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'wechat'"))
    push_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    wechat_msg_id: Mapped[str | None] = mapped_column(String(100))
    confirm_type: Mapped[str | None] = mapped_column(String(20), server_default=text("'none'"))
    confirm_status: Mapped[str | None] = mapped_column(String(20), server_default=text("'none'"))
    confirm_payload: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    confirm_reply: Mapped[str | None] = mapped_column(Text)
    confirm_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expire_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    max_retry: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("3"))
    last_retry_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    dedup_key: Mapped[str | None] = mapped_column(String(100))
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class RiskEvents(Base):
    __tablename__ = "risk_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_level: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(40), nullable=False)
    action_detail: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    recovery_path: Mapped[str | None] = mapped_column(String(10))
    recovery_status: Mapped[str | None] = mapped_column(String(20), server_default=text("'pending'"))
    recovery_deadline: Mapped[datetime | None] = mapped_column(Date)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    is_intraday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class RiskMetricsDaily(Base):
    __tablename__ = "risk_metrics_daily"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    daily_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    win_rate_3d: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    consecutive_loss_days: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    profit_loss_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    pl_ratio_rolling: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    consecutive_losses: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    total_position_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    position_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    annual_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    calmar_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    market_daily_change: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    qmt_failure_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    risk_status: Mapped[str | None] = mapped_column(String(20), server_default=text("'normal'"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("trade_date"),
    )


class Experiences(Base):
    __tablename__ = "experiences"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    market_state: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(32))
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(10))
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    operation_detail: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'"))
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    holding_days: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, server_default=text("50.0"))
    tags: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'"))
    scenario_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'real'"))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    last_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, server_default=text("100.0"))
    related_trade_id: Mapped[int | None] = mapped_column(BigInteger)
    feedback_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    __table_args__ = (
        UniqueConstraint("scenario_hash"),
    )


class AccountSyncLog(Base):
    __tablename__ = "account_sync_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)
    total_asset: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    available_cash: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    frozen_cash: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    daily_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    positions_json: Mapped[dict | None] = mapped_column(JSONB)
    sync_status: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'success'"))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class StopProfitConditions(Base):
    __tablename__ = "stop_profit_conditions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("positions.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    sell_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    triggered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))


class StopLossConditions(Base):
    __tablename__ = "stop_loss_conditions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("positions.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.code"), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stop_loss_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    trigger_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    trailing_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    max_loss_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    max_loss_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    triggered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    trigger_price_actual: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
