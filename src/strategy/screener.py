"""策略引擎 — 粗筛器

P0-3.1: 策略一「周期底部量能异动」
P0-3.2: 策略二「趋势动量低吸」
"""

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from src.data.db import get_db_connection

logger = logging.getLogger(__name__)


MIN_KLINES_FOR_SCREEN = 30
STRATEGY2_MIN_KLINES = 66


@dataclass
class StrategyCandidate:
    """粗筛候选标的"""
    stock_code: str
    stock_name: str
    score: float = 0.0
    drop_pct: float = 0.0
    daily_amount: float = 0.0
    reason: str = ""
    detail: dict = field(default_factory=dict)


# ── 策略一：周期底部量能异动 ──────────────────────────────────────

# 参数配置
STRATEGY1_DROP_60D_THRESHOLD = 20.0      # 近60日跌幅 ≥ 20%
STRATEGY1_DROP_5D_THRESHOLD = -5.0       # 近5日单日跌幅 ≥ 5%
STRATEGY1_MIN_MARKET_CAP = 5_000_000_000     # 市值 ≥ 50亿
STRATEGY1_MAX_MARKET_CAP = 50_000_000_000    # 市值 ≤ 500亿
STRATEGY1_MIN_DAILY_AMOUNT = 100_000_000     # 日均成交额 ≥ 1亿
STRATEGY1_MIN_DAYS_LISTED = 180            # 上市 ≥ 180天


def is_st_stock(stock_name: str | None) -> bool:
    """判断是否为ST/警示股"""
    if not stock_name:
        return True
    name = stock_name.upper()
    return name.startswith("ST") or name.startswith("*ST") or name.startswith("SST")


def is_new_stock(listing_date: date | None, today: date | None = None) -> bool:
    """判断是否为次新股（上市不足180天）"""
    if listing_date is None:
        return True
    ref = today or date.today()
    return (ref - listing_date).days < STRATEGY1_MIN_DAYS_LISTED


def has_drop_in_window(
    klines: pd.DataFrame,
    window: int = 5,
    threshold: float = -5.0,
) -> bool:
    """检测近N日内是否有单日大跌"""
    if klines.empty or "pct_change" not in klines.columns:
        return False
    recent = klines.tail(window)
    return bool((recent["pct_change"] <= threshold).any())


def has_sufficient_liquidity(
    klines: pd.DataFrame,
    min_daily_amount: int = 100_000_000,
    window: int = 20,
) -> bool:
    """检测日均成交额是否满足流动性要求"""
    if klines.empty or "amount" not in klines.columns:
        return False
    recent = klines.tail(min(window, len(klines)))
    avg_amount = recent["amount"].mean()
    return avg_amount >= min_daily_amount


# ── 策略二：趋势动量低吸 ──────────────────────────────────────────

STRATEGY2_SECTOR_CONCENTRATION = 12.0       # 板块资金集中度 ≥ 12%
STRATEGY2_MIN_ADX = 25.0                    # ADX ≥ 25
STRATEGY2_VOLUME_RATIO = 0.8               # 缩量 < 5日均量80%
STRATEGY2_PRICE_DROP_THRESHOLD = -3.0       # 回调跌幅 < 3%
STRATEGY2_MIN_DAILY_AMOUNT = 300_000_000    # 日均成交额 ≥ 3亿
STRATEGY2_SECTOR_CHECK_DAYS = 2             # 板块集中度连续检查天数


def is_bullish_arrangement(mas: dict[str, float]) -> bool:
    """检查均线多头排列：MA5 > MA10 > MA20 > MA60"""
    required = ["ma5", "ma10", "ma20", "ma60"]
    if not all(k in mas for k in required):
        return False
    return mas["ma5"] >= mas["ma10"] >= mas["ma20"] >= mas["ma60"]


def is_volume_shrinking(
    klines: pd.DataFrame,
    lookback: int = 3,
    ma_window: int = 5,
    ratio: float = 0.8,
) -> bool:
    """检测近N日成交量是否萎缩到均量的 ratio 以下"""
    if klines.empty or "volume" not in klines.columns:
        return False
    if len(klines) < max(lookback, ma_window) + 1:
        return False
    recent = klines.tail(lookback)["volume"].mean()
    avg = klines.tail(ma_window)["volume"].mean()
    if avg == 0:
        return False
    return recent < avg * ratio


def calculate_adx(klines: pd.DataFrame, period: int = 14) -> float:
    """计算 ADX（平均趋向指数）

    0-100 范围，>25 表示趋势较强。
    """
    if klines.empty:
        return 0.0

    required = {"high", "low", "close"}
    if not required.issubset(set(klines.columns)):
        return 0.0

    df = klines.copy()
    if len(df) < period + 1:
        return 0.0

    # TR（真实波幅）
    df["prev_close"] = df["close"].shift(1)
    df["tr1"] = abs(df["high"] - df["low"])
    df["tr2"] = abs(df["high"] - df["prev_close"])
    df["tr3"] = abs(df["low"] - df["prev_close"])
    df["tr"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

    # +DM / -DM
    df["up_move"] = df["high"] - df["high"].shift(1)
    df["down_move"] = df["low"].shift(1) - df["low"]
    df["+dm"] = np.where(
        (df["up_move"] > df["down_move"]) & (df["up_move"] > 0),
        df["up_move"], 0.0,
    )
    df["-dm"] = np.where(
        (df["down_move"] > df["up_move"]) & (df["down_move"] > 0),
        df["down_move"], 0.0,
    )

    # 平滑
    df["atr"] = df["tr"].ewm(span=period, adjust=False).mean()
    df["+di"] = 100 * df["+dm"].ewm(span=period, adjust=False).mean() / df["atr"]
    df["-di"] = 100 * df["-dm"].ewm(span=period, adjust=False).mean() / df["atr"]

    # DX → ADX
    df["dx"] = 100 * abs(df["+di"] - df["-di"]) / (df["+di"] + df["-di"] + 1e-10)
    df["adx"] = df["dx"].ewm(span=period, adjust=False).mean()

    return float(df["adx"].iloc[-1])


def screen_strategy2() -> list[StrategyCandidate]:  # noqa: PLR0912, PLR0915
    """策略二「趋势动量低吸」粗筛"""
    candidates: list[StrategyCandidate] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 0. 获取热点板块（连续2日资金集中度≥12%）
        cursor.execute("""
            SELECT sector_name, capital_ratio, trade_date
            FROM sector_data
            WHERE trade_date >= (
                SELECT MAX(trade_date) - INTERVAL '3 days'
                FROM sector_data
            )
            AND capital_ratio IS NOT NULL
            ORDER BY trade_date DESC, capital_ratio DESC
            LIMIT 20
        """)
        sector_rows = cursor.fetchall()

        hot_sector = ""
        sector_dates: dict[str, list[float]] = {}
        for name, ratio, _td in sector_rows:
            if name not in sector_dates:
                sector_dates[name] = []
            if ratio is not None:
                sector_dates[name].append(float(ratio))

        _sc2_days = STRATEGY2_SECTOR_CHECK_DAYS
        for name, ratios in sector_dates.items():
            if (
                len(ratios) >= STRATEGY2_SECTOR_CHECK_DAYS
                and all(r >= STRATEGY2_SECTOR_CONCENTRATION for r in ratios[:_sc2_days])
            ):
                hot_sector = name
                break

        if not hot_sector:
            logger.info("策略二: 无符合集中度要求的板块")
            cursor.close()
            conn.close()
            return []

        logger.info("策略二: 热点板块 %s", hot_sector)

        # 获取所有正常股票
        cursor.execute("""
            SELECT code, name, listing_date, market_cap
            FROM stocks
            WHERE status IS NULL OR status != 'D'
        """)
        all_stocks = cursor.fetchall()

        today = date.today()

        for code, name, listing_date, market_cap in all_stocks:  # noqa: B007
            if is_st_stock(name):  # strategy2 ST排除
                continue
            if is_new_stock(listing_date, today):
                continue

            cursor.execute("""
                SELECT high, low, close, volume, amount, pct_change
                FROM daily_klines
                WHERE stock_code = %s
                ORDER BY trade_date DESC
                LIMIT 80
            """, (code,))
            rows = cursor.fetchall()

            if len(rows) < STRATEGY2_MIN_KLINES:
                continue

            df = pd.DataFrame(
                rows,
                columns=["high", "low", "close", "volume", "amount", "pct_change"],
            )

            # 均线多头排列（用正序计算）
            df_sorted = df.iloc[::-1].reset_index(drop=True)
            df_sorted["ma5"] = df_sorted["close"].rolling(5).mean()
            df_sorted["ma10"] = df_sorted["close"].rolling(10).mean()
            df_sorted["ma20"] = df_sorted["close"].rolling(20).mean()
            df_sorted["ma60"] = df_sorted["close"].rolling(60).mean()

            mas = {
                "ma5": float(df_sorted["ma5"].iloc[-1]),
                "ma10": float(df_sorted["ma10"].iloc[-1]),
                "ma20": float(df_sorted["ma20"].iloc[-1]),
                "ma60": float(df_sorted["ma60"].iloc[-1]),
            }
            if not is_bullish_arrangement(mas):
                continue

            # ADX ≥ 25（ADX 计算在正序/倒序上结果一致，但用正序更标准）
            adx = calculate_adx(df_sorted, period=14)
            if adx < STRATEGY2_MIN_ADX:
                continue

            # 缩量回调
            if not is_volume_shrinking(  # noqa: E501
                df_sorted, lookback=3, ma_window=5, ratio=STRATEGY2_VOLUME_RATIO
            ):
                continue

            if "pct_change" in df.columns:
                recent_pct = df.head(3)["pct_change"].mean()
                if recent_pct < STRATEGY2_PRICE_DROP_THRESHOLD:
                    continue

            if not has_sufficient_liquidity(df_sorted, min_daily_amount=STRATEGY2_MIN_DAILY_AMOUNT):
                continue

            avg_amount = df["amount"].mean()
            candidates.append(StrategyCandidate(
                stock_code=code,
                stock_name=name,
                score=round(adx, 1),
                daily_amount=avg_amount,
                reason=f"板块:{hot_sector} ADX:{adx:.1f} 多头排列+缩量回调",
            ))

        cursor.close()
        conn.close()

        logger.info("策略二粗筛: %d 只候选", len(candidates))
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    except Exception as e:
        logger.error("策略二粗筛失败: %s", e)
        return []


# ── 策略一：周期底部量能异动 ──────────────────────────────────────

def screen_strategy1() -> list[StrategyCandidate]:
    """策略一「周期底部量能异动」粗筛"""
    candidates: list[StrategyCandidate] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT code, name, listing_date, market_cap
            FROM stocks
            WHERE status IS NULL OR status != 'D'
        """)
        all_stocks = cursor.fetchall()

        today = date.today()

        for code, name, listing_date, market_cap in all_stocks:  # noqa: B007
            if is_st_stock(name):  # strategy2 ST排除
                continue
            if is_new_stock(listing_date, today):
                continue
            if market_cap is not None and (
                market_cap < STRATEGY1_MIN_MARKET_CAP or
                market_cap > STRATEGY1_MAX_MARKET_CAP
            ):
                continue

            cursor.execute("""
                SELECT trade_date, open, high, low, close, volume, amount, pct_change
                FROM daily_klines
                WHERE stock_code = %s
                ORDER BY trade_date DESC
                LIMIT 80
            """, (code,))
            rows = cursor.fetchall()

            if len(rows) < MIN_KLINES_FOR_SCREEN:
                continue

            df = pd.DataFrame(
                rows,
                columns=[
                    "trade_date", "open", "high", "low", "close",
                    "volume", "amount", "pct_change",
                ],
            )

            first_close = df.iloc[-1]["close"]
            last_close = df.iloc[0]["close"]
            if pd.notna(first_close) and pd.notna(last_close) and first_close > 0:
                drop_pct = (first_close - last_close) / first_close * 100
            else:
                continue

            if drop_pct < STRATEGY1_DROP_60D_THRESHOLD:
                continue
            if not has_drop_in_window(df, window=5, threshold=STRATEGY1_DROP_5D_THRESHOLD):
                continue
            if not has_sufficient_liquidity(df, min_daily_amount=STRATEGY1_MIN_DAILY_AMOUNT):
                continue

            avg_amount = df["amount"].mean()
            candidates.append(StrategyCandidate(
                stock_code=code,
                stock_name=name,
                score=round(drop_pct, 1),
                drop_pct=round(drop_pct, 1),
                daily_amount=avg_amount,
                reason=f"近60日跌幅{drop_pct:.1f}%，近5日出现大跌",
            ))

        cursor.close()
        conn.close()
        logger.info("策略一粗筛: %d 只候选", len(candidates))
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    except Exception as e:
        logger.error("策略一粗筛失败: %s", e)
        return []
