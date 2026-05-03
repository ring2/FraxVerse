"""市场和行情相关 Schemas"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class KlineItem(BaseModel):
    stock_code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    ma5: Decimal | None = None
    ma10: Decimal | None = None
    ma20: Decimal | None = None


class NewsItem(BaseModel):
    id: int
    source: str
    source_display: str = ""
    title: str
    published_at: datetime
    sentiment: str | None = None
    related_stocks: list[str] = []
    is_hot: bool = False
    hot_score: int = 0


class SectorItem(BaseModel):
    sector_name: str
    sector_type: str
    change_pct: Decimal | None = None
    capital_ratio: Decimal | None = None
    leader_stocks: list[str] = []


class MarketStateResponse(BaseModel):
    date: date
    current_state: str
    main_line_sector: str | None = None
    confidence: float | None = None


class MacroeconomicItem(BaseModel):
    indicator_name: str
    value: Decimal | None = None
    period: str
    published_at: datetime | None = None
