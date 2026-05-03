"""行情路由 — /api/v1/market/*"""

import re
from datetime import date

import akshare as ak
import pandas as pd
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.models import DailyKlines, MarketStateLog, News, SectorData
from src.db.session import get_session
from src.schemas.market import (
    KlineItem,
    KlineSimpleItem,
    MarketStateResponse,
    MultiPeriodKlineItem,
    NewsItem,
    NewsPageResponse,
    SectorItem,
    StockDetailResponse,
)

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


@router.get("/news", response_model=NewsPageResponse)
def get_news(
    source: str | None = None,
    hot_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询新闻 — 按热度分页，再按时间排序，返回 {items, total}"""
    q = db.query(News).order_by(News.hot_score.desc(), News.published_at.desc())
    if source:
        q = q.filter(News.source == source)
    if hot_only:
        q = q.filter(News.is_hot)
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {"items": items, "total": total}


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


@router.get("/klines-multi", response_model=list[MultiPeriodKlineItem])
def get_klines_multi(
    code: str = Query(..., description="股票代码，如 600519"),
    period: str = Query("daily", description="周期: daily|weekly|monthly|1|15|30"),
    limit: int = Query(120, ge=10, le=500),
    user_id: int = Depends(get_current_user_id),
):
    """多周期K线 — 通过AKShare实时获取，前端绘图用"""
    raw = code.upper().strip()
    raw = re.sub(r"\.(SH|SZ|BJ)$", "", raw)

    # 分时周期（1/5/15/30/60分钟）→ stock_zh_a_hist_min_em
    minute_periods = {"1", "5", "15", "30", "60"}
    # 日/周/月周期
    date_periods = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}

    try:
        if period in date_periods:
            df = ak.stock_zh_a_hist(symbol=raw, period=period, adjust="qfq")
            if df is None or df.empty:
                return []
            df = df.tail(limit)

            rows: list[MultiPeriodKlineItem] = []
            for _, row in df.iterrows():
                rows.append(MultiPeriodKlineItem(
                    timestamp=str(row.get("日期", "")),
                    open=float(row.get("开盘", 0) or 0),
                    high=float(row.get("最高", 0) or 0),
                    low=float(row.get("最低", 0) or 0),
                    close=float(row.get("收盘", 0) or 0),
                    volume=float(row.get("成交量", 0) or 0),
                    amount=float(row.get("成交额", 0) or 0),
                    change_pct=float(row.get("涨跌幅", 0) or 0),
                ))
            return rows

        elif period in minute_periods:
            # 取最近7天的分钟线
            from datetime import datetime, timedelta

            end = datetime.now()
            start = end - timedelta(days=30)  # 给足够窗口
            start_str = start.strftime("%Y-%m-%d 09:00:00")
            end_str = end.strftime("%Y-%m-%d %H:%M:%S")

            df = ak.stock_zh_a_hist_min_em(
                symbol=raw,
                period=period,
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",
            )
            if df is None or df.empty:
                return []
            df = df.tail(limit)

            rows: list[MultiPeriodKlineItem] = []
            for _, row in df.iterrows():
                ts = str(row.get("时间", row.get("day", "")))
                rows.append(MultiPeriodKlineItem(
                    timestamp=ts,
                    open=float(row.get("开盘", 0) or 0),
                    high=float(row.get("最高", 0) or 0),
                    low=float(row.get("最低", 0) or 0),
                    close=float(row.get("收盘", 0) or 0),
                    volume=float(row.get("成交量", 0) or 0),
                    amount=float(row.get("成交额", 0) or 0),
                    change_pct=float(row.get("涨跌幅", 0) or 0),
                ))
            return rows

        else:
            raise HTTPException(status_code=400, detail=f"不支持的周期: {period}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取{period}K线失败: {e}")


@router.get("/stock-detail", response_model=StockDetailResponse)
def get_stock_detail(
    code: str = Query(..., description="股票代码，如 600519"),
    user_id: int = Depends(get_current_user_id),
):
    """个股详情：东方财富 push2 实时行情 + AKShare hist 日K"""
    raw = code.upper().strip()
    raw = re.sub(r"\.(SH|SZ|BJ)$", "", raw)

    # 交易所 secid 映射
    if raw.startswith(("6", "9")):
        market = 1  # 上交所
    elif raw.startswith(("0", "3")):
        market = 0  # 深交所
    elif raw.startswith(("4", "8")):
        market = 2  # 北交所
    else:
        market = 1

    # 1) 实时行情 — 东方财富 push2 个股接口
    try:
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": f"{market}.{raw}",
            "fields": (
                "f43,f44,f45,f46,f47,f48,f49,f50,"
                "f57,f58,f116,f117,"
                "f162,f167,f168,f169,f170,f171,f292"
            ),
        }
        resp = requests.get(url, params=params, timeout=5)
        body = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取实时行情失败: {e}")

    if body.get("rc") != 0 or not body.get("data"):
        raise HTTPException(status_code=404, detail=f"未找到股票 {raw}")

    d = body["data"]

    def _v(key: str, div: int = 1, default: float = 0.0) -> float:
        val = d.get(key)
        if val is None:
            return default
        return float(val) / div

    # 昨收：用前收盘价 f60 或 f46 倒推
    pre_close = _v("f46", 100)  # 昨收缺省用今开
    # 尝试用 hist 拿更准的昨收（在下面补充）
    amount_yuan = _v("f48")

    detail = StockDetailResponse(
        code=raw,
        name=str(d.get("f58", "")),
        price=_v("f43", 100),
        change_pct=_v("f170", 100),
        change_amount=_v("f169", 100),
        open=_v("f46", 100),
        high=_v("f44", 100),
        low=_v("f45", 100),
        pre_close=pre_close,
        volume=_v("f47"),
        amount=amount_yuan,
        turnover_rate=_v("f168", 100),
        volume_ratio=_v("f49", 10000),
        pe=_v("f162", 100),
        pb=_v("f167", 100),
        total_value=_v("f116"),
        circulate_value=_v("f117"),
    )

    # 2) 日K + 补充换手率/昨收 — AKShare hist
    try:
        hist = ak.stock_zh_a_hist(symbol=raw, period="daily", adjust="qfq")
        if not hist.empty:
            hist = hist.tail(90)
            latest = hist.iloc[-1]
            if latest.get("换手率"):
                detail.turnover_rate = float(latest["换手率"])
            if len(hist) >= 2:
                detail.pre_close = float(hist.iloc[-2].get("收盘", 0) or 0)
            klines = [
                KlineSimpleItem(
                    trade_date=str(hrow["日期"]),
                    open=float(hrow.get("开盘", 0)),
                    high=float(hrow.get("最高", 0)),
                    low=float(hrow.get("最低", 0)),
                    close=float(hrow.get("收盘", 0)),
                    volume=float(hrow.get("成交量", 0)),
                    change_pct=float(hrow.get("涨跌幅", 0) or 0),
                )
                for _, hrow in hist.iterrows()
            ]
            detail.klines = klines
    except Exception:
        pass

    return detail
