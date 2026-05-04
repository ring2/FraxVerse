"""策略引擎 — 粗筛器

P0-3.1: 策略一「周期底部量能异动」
P0-3.2: 策略二「趋势动量低吸」
"""

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from src.config_loader import load_strategy_config
from src.data.db import get_db_connection
from src.db.session import get_session

logger = logging.getLogger(__name__)



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


def _get_strategy_config():
    from src.db.session import get_session
    db = get_session()
    try:
        return load_strategy_config(db)
    finally:
        db.close()


def is_st_stock(stock_name: str | None) -> bool:
    """判断是否为ST/警示股"""
    if not stock_name:
        return True
    name = stock_name.upper()
    return name.startswith("ST") or name.startswith("*ST") or name.startswith("SST")


def is_new_stock(listing_date: date | None, today: date | None = None, config: dict | None = None) -> bool:
    """判断是否为次新股（上市不足180天）"""
    if listing_date is None:
        return True
    ref = today or date.today()
    if config is None:
        config = _get_strategy_config()
    return (ref - listing_date).days < config["min_days_listed"]


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


def screen_strategy2(config: dict | None = None) -> list[StrategyCandidate]:  # noqa: PLR0912, PLR0915
    """策略二「趋势动量低吸」粗筛"""
    if config is None:
        config = _get_strategy_config()

    candidates: list[StrategyCandidate] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 0. 获取热点板块（连续N日资金集中度≥阈值）
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

        _sector_check_days = config["sector_check_days"]
        _sector_concentration = config["sector_concentration"]
        for name, ratios in sector_dates.items():
            if (
                len(ratios) >= _sector_check_days
                and all(r >= _sector_concentration for r in ratios[:_sector_check_days])
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
            SELECT code, name, list_date
            FROM stocks
            WHERE is_suspended = false
        """)
        all_stocks = cursor.fetchall()

        today = date.today()

        for code, name, list_date in all_stocks:  # noqa: B007
            if is_st_stock(name):  # strategy2 ST排除
                continue
            if is_new_stock(list_date, today, config):
                continue

            cursor.execute("""
                SELECT high, low, close, volume, amount, pct_change
                FROM daily_klines
                WHERE stock_code = %s
                ORDER BY trade_date DESC
                LIMIT 80
            """, (code,))
            rows = cursor.fetchall()

            if len(rows) < config["min_klines_s2"]:
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

            # ADX ≥ 阈值（ADX 计算在正序/倒序上结果一致，但用正序更标准）
            adx = calculate_adx(df_sorted, period=14)
            if adx < config["min_adx"]:
                continue

            # 缩量回调
            if not is_volume_shrinking(
                df_sorted, lookback=3, ma_window=5, ratio=config["volume_ratio"],
            ):
                continue

            if "pct_change" in df.columns:
                recent_pct = df.head(3)["pct_change"].mean()
                if recent_pct < config["price_drop_threshold_s2"]:
                    continue

            if not has_sufficient_liquidity(df_sorted, min_daily_amount=config["min_daily_amount_s2"]):
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

def screen_strategy1(config: dict | None = None) -> list[StrategyCandidate]:
    """策略一「周期底部量能异动」粗筛"""
    if config is None:
        config = _get_strategy_config()

    candidates: list[StrategyCandidate] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT code, name, list_date
            FROM stocks
            WHERE is_suspended = false
        """)
        all_stocks = cursor.fetchall()

        today = date.today()

        for code, name, list_date in all_stocks:  # noqa: B007
            if is_st_stock(name):  # strategy1 ST排除
                continue
            if is_new_stock(list_date, today, config):
                continue

            cursor.execute("""
                SELECT trade_date, open, high, low, close, volume, amount, pct_change
                FROM daily_klines
                WHERE stock_code = %s
                ORDER BY trade_date DESC
                LIMIT 80
            """, (code,))
            rows = cursor.fetchall()

            if len(rows) < config["min_klines_s1"]:
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

            if drop_pct < config["drop_60d_threshold"]:
                continue
            if not has_drop_in_window(df, window=5, threshold=config["drop_5d_threshold"]):
                continue
            if not has_sufficient_liquidity(df, min_daily_amount=config["min_daily_amount"]):
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
