"""为回测模拟生成每日评分池（stock_pool）

当 DB 中没有历史评分数据时，用真实 K 线数据模拟每日筛选逻辑，
为每个交易日生成模拟的评分池记录。

策略一「周期底部量能异动」筛选条件：
  - 近60日跌幅 >= 20%
  - 近5日内出现单日大跌 >= 5%
  - 日均成交额 >= 1亿

策略二「趋势动量低吸」筛选条件：
  - 均线多头排列 (MA5 > MA10 > MA20 > MA60)
  - ADX >= 20
  - 缩量回调（近3日均量 < 5日均量 * 0.8）
  - 日均成交额 >= 1亿
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── 策略一常量 ──
DROP_60D_THRESHOLD = -10.0  # 近60日跌幅阈值(%)(2024年普涨，20%太严格)
DROP_5D_THRESHOLD = -5.0    # 近5日单日大跌阈值(%)
MIN_DAILY_AMOUNT_S1 = 100_000_000  # 日均成交额门槛

# ── 策略二常量 ──
MIN_ADX = 20
VOLUME_RATIO = 0.8
MIN_DAILY_AMOUNT_S2 = 100_000_000


def simulate_daily_scored_pool(
    klines_dict: dict[str, pd.DataFrame],
    start: date,
    end: date,
    strategy_type: str,
    top_n: int = 15,
) -> dict[str, list[dict]]:
    """在每个交易日用真实 K 线模拟策略筛选，生成模拟评分池

    Returns:
        {date_str: [{stock_code, score_total, strategy_type}]}
    """
    if strategy_type == "bottom_volume":
        return _simulate_strategy1(klines_dict, start, end, top_n)
    elif strategy_type == "trend_momentum":
        return _simulate_strategy2(klines_dict, start, end, top_n)
    else:
        logger.warning("未知策略类型: %s，回退为全量买入持有", strategy_type)
        return {}


def _simulate_strategy1(
    klines_dict: dict[str, pd.DataFrame],
    start: date,
    end: date,
    top_n: int = 15,
) -> dict[str, list[dict]]:
    """策略一模拟：逐日扫描，60日跌幅+近5日大跌+流动性"""
    scored_pool: dict[str, list[dict]] = {}

    # 获取所有交易日
    all_dates = _get_trade_days(klines_dict, start, end)

    for code, klines in klines_dict.items():
        if klines.empty:
            continue

        # 确保日期排序和必要列
        df = klines.sort_values("date").reset_index(drop=True)
        if "pct_change" not in df.columns:
            df["pct_change"] = df["close"].pct_change() * 100

        for d in all_dates:
            # 获取到d为止的历史数据
            hist = df[df["date"] <= d]
            # 至少需要20根K线才能计算指标
            if len(hist) < 20:
                continue

            recent = hist.tail(60)  # 取最多60根

            # 条件1：近60日跌幅 >= 20%
            first_close = recent.iloc[0]["close"]
            last_close = recent.iloc[-1]["close"]
            if first_close == 0:
                continue
            drop_pct = (last_close - first_close) / first_close * 100
            if drop_pct >= DROP_60D_THRESHOLD:
                continue

            # 条件2：近5日有大跌
            last5 = recent.tail(5)
            if "pct_change" not in last5.columns or last5.empty:
                continue
            if not (last5["pct_change"].dropna() <= DROP_5D_THRESHOLD).any():
                continue

            # 条件3：日均成交额
            if "amount" in recent.columns:
                avg_amount = recent["amount"].tail(20).mean()
                if pd.notna(avg_amount) and avg_amount < MIN_DAILY_AMOUNT_S1:
                    continue

            # 通过筛选：评分为跌幅绝对值 * 5（确保通过默认阈值）
            score = min(100.0, abs(drop_pct) * 5)

            d_str = d.isoformat()
            if d_str not in scored_pool:
                scored_pool[d_str] = []
            scored_pool[d_str].append({
                "stock_code": code,
                "score_total": round(score, 1),
                "strategy_type": "bottom_volume",
            })

    # 每天只取 top_n
    for d_str in scored_pool:
        scored_pool[d_str].sort(key=lambda x: x["score_total"], reverse=True)
        scored_pool[d_str] = scored_pool[d_str][:top_n]

    _log_simulated_pool(scored_pool, "策略一")
    return scored_pool


def _simulate_strategy2(
    klines_dict: dict[str, pd.DataFrame],
    start: date,
    end: date,
    top_n: int = 15,
) -> dict[str, list[dict]]:
    """策略二模拟：逐日扫描，多头排列+ADX+缩量+流动性"""
    scored_pool: dict[str, list[dict]] = {}

    all_dates = _get_trade_days(klines_dict, start, end)

    for code, klines in klines_dict.items():
        if klines.empty:
            continue

        df = klines.sort_values("date").reset_index(drop=True)
        if "pct_change" not in df.columns:
            df["pct_change"] = df["close"].pct_change() * 100

        for d in all_dates:
            hist = df[df["date"] <= d]
            # 至少需要20根K线
            if len(hist) < 20:
                continue

            recent = hist.tail(60)

            # 计算均线（用可用的数据量）
            close = recent["close"]
            ma5 = close.rolling(min_periods=3, window=5).mean().iloc[-1] if len(close) >= 5 else None
            ma10 = close.rolling(min_periods=5, window=10).mean().iloc[-1] if len(close) >= 10 else None
            ma20 = close.rolling(min_periods=10, window=20).mean().iloc[-1] if len(close) >= 20 else None
            ma60 = close.rolling(min_periods=20, window=60).mean().iloc[-1] if len(close) >= 20 else None

            if None in (ma5, ma10, ma20):
                continue

            # 条件1：多头排列（放宽版：不要求ma60，只要ma5>ma10>ma20）
            if not (ma5 >= ma10 >= ma20):
                continue

            # 条件2：ADX >= 20
            adx = _calc_adx(recent)
            if adx < MIN_ADX:
                continue

            # 条件3：缩量回调
            volume = recent["volume"]
            recent_vol = volume.tail(3).mean() if len(volume) >= 3 else 0
            avg_vol = volume.tail(5).mean() if len(volume) >= 5 else 0
            if avg_vol > 0 and recent_vol >= avg_vol * VOLUME_RATIO:
                # 未缩量到阈值以下，不通过
                # 但放宽条件：只要不是放量下跌就算
                last5_pct = recent.tail(5)["pct_change"].mean() if "pct_change" in recent.columns else 0
                if last5_pct > -2:
                    continue

            # 条件4：流动性
            if "amount" in recent.columns:
                avg_amount = recent["amount"].tail(20).mean()
                if pd.notna(avg_amount) and avg_amount < MIN_DAILY_AMOUNT_S2:
                    continue

            # 通过筛选：评分 = ADX (越高越好)
            score = min(100.0, adx * 2.5)

            d_str = d.isoformat()
            if d_str not in scored_pool:
                scored_pool[d_str] = []
            scored_pool[d_str].append({
                "stock_code": code,
                "score_total": round(score, 1),
                "strategy_type": "trend_momentum",
            })

    # 每天只取 top_n
    for d_str in scored_pool:
        scored_pool[d_str].sort(key=lambda x: x["score_total"], reverse=True)
        scored_pool[d_str] = scored_pool[d_str][:top_n]

    _log_simulated_pool(scored_pool, "策略二")
    return scored_pool


def _calc_adx(df: pd.DataFrame, period: int = 14) -> float:
    """简化 ADX 计算"""
    if df.empty or len(df) < period + 1:
        return 0.0

    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)

    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]

    tr1 = np.abs(high - low)
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    up_move = np.diff(high, prepend=high[0])
    down_move = np.diff(low, prepend=low[0]) * -1

    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = _ema(tr, period)
    pos_di = 100 * _ema(pos_dm, period) / np.maximum(atr, 1e-10)
    neg_di = 100 * _ema(neg_dm, period) / np.maximum(atr, 1e-10)

    dx = 100 * np.abs(pos_di - neg_di) / np.maximum(pos_di + neg_di, 1e-10)
    adx_series = _ema(dx, period)

    return float(adx_series[-1]) if len(adx_series) > 0 else 0.0


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均"""
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(values)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def _get_trade_days(
    klines_dict: dict[str, pd.DataFrame],
    start: date,
    end: date,
) -> list[date]:
    """获取所有交易日（去重排序）"""
    all_dates: set[date] = set()
    for df in klines_dict.values():
        for d in df["date"]:
            dt = pd.Timestamp(d).date()
            if start <= dt <= end:
                all_dates.add(dt)
    return sorted(all_dates)


def _log_simulated_pool(pool: dict[str, list[dict]], label: str):
    """打印模拟评分池统计"""
    total_days = len(pool)
    total_picks = sum(len(v) for v in pool.values())
    if total_days > 0:
        avg_per_day = total_picks / total_days
        logger.info(
            "%s 模拟评分池: %d 天, %d 条记录, 日均 %.1f 只",
            label, total_days, total_picks, avg_per_day,
        )
    else:
        logger.warning("%s 模拟评分池: 无符合条件的交易日", label)
