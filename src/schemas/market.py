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
    url: str | None = None
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


class NewsPageResponse(BaseModel):
    items: list[NewsItem]
    total: int


class MarketStateResponse(BaseModel):
    date: date
    current_state: str
    main_line_sector: str | None = None
    confidence: float | None = None


class KlineSimpleItem(BaseModel):
    """简化日K线（前端绘图用）"""
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    change_pct: float = 0.0


class MultiPeriodKlineItem(BaseModel):
    """多周期K线（1/5/15/30/60分钟 + 日/周）"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    change_pct: float = 0.0


class StockDetailResponse(BaseModel):
    """个股详情（实时行情 + 日K）"""
    code: str
    name: str
    price: float = 0.0
    change_pct: float = 0.0
    change_amount: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: float = 0.0          # 成交量（手）
    amount: float = 0.0          # 成交额（亿）
    turnover_rate: float = 0.0   # 换手率（%）
    volume_ratio: float = 0.0    # 量比
    inner_disc: float = 0.0      # 内盘
    outer_disc: float = 0.0      # 外盘
    total_value: float = 0.0     # 总市值（亿）
    circulate_value: float = 0.0 # 流通市值（亿）
    pe: float = 0.0              # 市盈率
    pb: float = 0.0              # 市净率
    klines: list[KlineSimpleItem] = []


class MacroeconomicItem(BaseModel):
    indicator_name: str
    value: Decimal | None = None
    period: str
    published_at: datetime | None = None
