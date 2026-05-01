"""交易相关 Schemas"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    stock_code: str = Field(..., pattern=r"^\d{6}\.(SH|SZ|BJ)$")
    direction: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^(market|limit)$")
    price: Decimal | None = None
    volume: int = Field(..., gt=0)
    strategy_type: str | None = None
    reason: str | None = None


class OrderResponse(BaseModel):
    id: int
    client_order_id: str
    stock_code: str
    direction: str
    status: str
    volume: int
    filled_volume: int
    price: Decimal | None = None
    created_at: datetime


class PositionItem(BaseModel):
    stock_code: str
    stock_name: str | None = None
    total_volume: int
    available_volume: int
    cost_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    position_pct: Decimal
    entry_date: date | None = None


class TradeRecord(BaseModel):
    id: int
    stock_code: str
    direction: str
    status: str
    volume: int
    price: Decimal | None = None
    filled_amount: Decimal | None = None
    strategy_type: str | None = None
    reason: str | None = None
    created_at: datetime


class TradeModeResponse(BaseModel):
    current_mode: str
    confirm_mode: str
    emergency_stop: bool


class TradeModeUpdateRequest(BaseModel):
    target_mode: str = Field(..., pattern="^(SIMULATION|PAPER|LIVE)$")
    mode_password: str | None = None


class StockPoolItem(BaseModel):
    date: date
    stock_code: str
    strategy_type: str
    pass_coarse: bool
    score_total: Decimal | None = None
    final_decision: str | None = None
    position_pct: Decimal | None = None
    reject_reason: str | None = None
