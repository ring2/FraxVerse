"""风控、系统监控、经验库 Schemas"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class RiskEventItem(BaseModel):
    id: int
    event_type: str
    event_level: str
    trigger_reason: str
    action_taken: str
    trade_date: date
    created_at: datetime


class RiskMetricsItem(BaseModel):
    trade_date: date
    daily_drawdown: Decimal | None = None
    win_rate: Decimal | None = None
    consecutive_loss_days: int = 0
    total_position_pct: Decimal | None = None
    risk_status: str = "normal"


class ServiceStatus(BaseModel):
    service: str
    status: str
    uptime_seconds: float | None = None
    last_error: str | None = None


class SystemResource(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float


class ExperienceItem(BaseModel):
    id: int
    market_state: str
    strategy_type: str
    operation: str
    result: str
    pnl_pct: Decimal | None = None
    score: float
    confidence: float
    tags: list[str] = []
    created_at: datetime


class BacktestResultItem(BaseModel):
    id: int
    strategy_type: str
    start_date: date
    end_date: date
    annual_return: Decimal | None = None
    max_drawdown: Decimal | None = None
    win_rate: Decimal | None = None
    profit_loss_ratio: Decimal | None = None
    total_trades: int | None = None
    created_at: datetime


class PortfolioSummary(BaseModel):
    total_asset: Decimal | None = None
    available_cash: Decimal | None = None
    total_position_pct: Decimal | None = None
    daily_pnl: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    position_count: int = 0


class NotificationItem(BaseModel):
    id: int
    event_type: str
    priority: str
    title: str
    content: str
    is_read: bool = False
    created_at: datetime
