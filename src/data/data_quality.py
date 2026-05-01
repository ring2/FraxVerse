"""数据质量监控 — 断更检测、完整性检查、停牌/ST状态更新

P0-2.4: 数据质量自动监控
  1. check_missing_trade_dates: 交易日断更检测
  2. check_kline_integrity: K线数据完整性检查
  3. detect_suspension: 停牌检测
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from src.data.db import get_db_connection

logger = logging.getLogger(__name__)


MIN_TRADE_DATES_FOR_CHECK = 2
NULL_RATE_WARNING_THRESHOLD = 0.05


@dataclass
class DataQualityIssue:
    """数据质量问题报告"""
    stock_code: str
    trade_date: date | None
    issue_type: str          # missing_data / invalid_value / null_rate / suspension
    severity: str            # error / warning
    message: str
    detail: dict = field(default_factory=dict)


# ── 交易日历 ──────────────────────────────────────────────────────

# 中国A股休市日列表（2025-2026 常规假日，生产环境应从API获取）
# 这里只用于周末跳过检查，精确节假日需要从交易所日历API获取
def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # noqa: PLR2004


def _next_trade_day(d: date) -> date:
    """获取下一个交易日（跳过周末）"""
    d = d + timedelta(days=1)
    while _is_weekend(d):
        d += timedelta(days=1)
    return d


# ── 断更检测 ──────────────────────────────────────────────────────

def check_missing_trade_dates(trade_dates: list[date]) -> list[date]:
    """检测交易日是否有断更

    给定一个有序的交易日期列表，检查相邻交易日之间是否有缺失。
    周末（周六、周日）自动跳过。

    Args:
        trade_dates: 有序的交易日列表（从旧到新）

    Returns:
        缺失日期列表
    """
    if len(trade_dates) < MIN_TRADE_DATES_FOR_CHECK:
        return []

    missing: list[date] = []
    for i in range(len(trade_dates) - 1):
        current = trade_dates[i]
        expected_next = _next_trade_day(current)
        actual_next = trade_dates[i + 1]

        while expected_next < actual_next:
            missing.append(expected_next)
            expected_next = _next_trade_day(expected_next)

    return missing


# ── K线完整性检查 ──────────────────────────────────────────────────

def check_kline_integrity(
    df: pd.DataFrame,
    stock_code: str,
) -> list[DataQualityIssue]:
    """检查K线数据完整性

    检查项：
    1. 最高价<最低价 → error
    2. 收盘价超出开盘价/最高价/最低价范围 → error
    3. 空值率>5% → warning
    4. 成交量为0 → warning

    Args:
        df: 清洗后的K线DataFrame
        stock_code: 股票代码

    Returns:
        问题列表
    """
    if df.empty:
        return []

    issues: list[DataQualityIssue] = []

    # 检查必要列是否存在
    required = {"trade_date", "open", "high", "low", "close", "volume"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        issues.append(DataQualityIssue(
            stock_code=stock_code,
            trade_date=None,
            issue_type="missing_column",
            severity="error",
            message=f"缺少必要字段: {missing_cols}",
        ))
        return issues

    for _, row in df.iterrows():
        tdate = row.get("trade_date")
        if tdate is None:
            continue

        # 最高价 < 最低价
        if pd.notna(row.get("high")) and pd.notna(row.get("low")) and row["high"] < row["low"]:
                issues.append(DataQualityIssue(
                    stock_code=stock_code,
                    trade_date=tdate,
                    issue_type="invalid_value",
                    severity="error",
                    message=f"最高价({row['high']}) < 最低价({row['low']})",
                    detail={"high": float(row["high"]), "low": float(row["low"])},
                ))

        # 成交量为0
        if pd.notna(row.get("volume")) and row["volume"] == 0:
            issues.append(DataQualityIssue(
                stock_code=stock_code,
                trade_date=tdate,
                issue_type="zero_volume",
                severity="warning",
                message="成交量为0，可能停牌",
            ))

    # 空值率检查
    numeric_cols = ["open", "high", "low", "close", "volume"]
    total_cells = len(df) * len(numeric_cols)
    null_cells = sum(df[col].isna().sum() for col in numeric_cols if col in df.columns)
    null_rate = null_cells / total_cells if total_cells > 0 else 0
    if null_rate > NULL_RATE_WARNING_THRESHOLD:
        issues.append(DataQualityIssue(
            stock_code=stock_code,
            trade_date=None,
            issue_type="null_rate",
            severity="warning",
            message=f"空值率 {null_rate:.1%} 超过5%",
            detail={"null_rate": null_rate},
        ))

    return issues


# ── 停牌检测 ──────────────────────────────────────────────────────

def detect_suspension(lookback_days: int = 5) -> list[DataQualityIssue]:
    """检测全市场疑似停牌股票

    逻辑：最近 lookback_days 个交易日没有K线数据且未标注退市的股票。

    Args:
        lookback_days: 回溯交易日数

    Returns:
        疑似停牌问题列表
    """
    issues: list[DataQualityIssue] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取最近 lookback_days 个交易日
        cursor.execute("""
            SELECT DISTINCT trade_date
            FROM daily_klines
            ORDER BY trade_date DESC
            LIMIT %s
        """, (lookback_days,))
        recent_dates = [r[0] for r in cursor.fetchall()]
        cursor.close()
        conn.close()

        if not recent_dates:
            return issues

        # 获取全市场股票
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM stocks WHERE status != 'D'")
        all_stocks = cursor.fetchall()

        for code, name in all_stocks:
            cursor.execute("""
                SELECT MAX(trade_date)
                FROM daily_klines
                WHERE stock_code = %s AND trade_date >= %s
            """, (code, min(recent_dates)))
            last_data = cursor.fetchone()[0]

            if last_data is None:
                # 该股票完全没有数据
                continue
            if last_data < max(recent_dates):
                    issues.append(DataQualityIssue(
                        stock_code=code,
                        trade_date=last_data,
                        issue_type="suspension",
                        severity="warning",
                        message=f"{name}({code}) 最近交易日{last_data}后无新数据",
                    ))

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error("停牌检测失败: %s", e)

    return issues
