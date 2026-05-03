"""行情路由 — /api/v1/market/*"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.models import DailyKlines, MarketStateLog, News, SectorData
from src.db.session import get_session
from src.schemas.market import KlineItem, MarketStateResponse, NewsItem, SectorItem

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/klines", response_model=list[KlineItem])
def get_klines(
    stock_code: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(60, le=500),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询日K线数据"""
    q = db.query(DailyKlines).filter(DailyKlines.stock_code == stock_code)
    if start_date:
        q = q.filter(DailyKlines.trade_date >= start_date)
    if end_date:
        q = q.filter(DailyKlines.trade_date <= end_date)
    return q.order_by(DailyKlines.trade_date.desc()).limit(limit).all()


@router.get("/news", response_model=list[NewsItem])
def get_news(
    source: str | None = None,
    hot_only: bool = False,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询新闻 — 按热度分页，再按时间排序"""
    q = db.query(News).order_by(News.hot_score.desc(), News.published_at.desc())
    if source:
        q = q.filter(News.source == source)
    if hot_only:
        q = q.filter(News.is_hot)
    return q.limit(limit).all()


@router.get("/sectors", response_model=list[SectorItem])
def get_sectors(
    sector_type: str | None = None,
    date_str: date | None = None,
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询板块数据"""
    q = db.query(SectorData).order_by(SectorData.trade_date.desc())
    if date_str:
        q = q.filter(SectorData.trade_date == date_str)
    if sector_type:
        q = q.filter(SectorData.sector_type == sector_type)
    return q.limit(50).all()


@router.get("/market-state", response_model=list[MarketStateResponse])
def get_market_state(
    limit: int = Query(10, le=100),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询市场状态历史"""
    logs = db.query(MarketStateLog).order_by(MarketStateLog.date.desc()).limit(limit).all()
    return [
        MarketStateResponse(
            date=log.date,
            current_state=log.to_state,
            main_line_sector=log.main_line_sector,
            confidence=float(log.confidence) if log.confidence else None,
        )
        for log in logs
    ]
