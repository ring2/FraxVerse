"""AKShare 数据采集器 — 日K线数据采集、清洗、入库

P0-2.1: 日K线数据采集与入库
  1. fetch_daily_kline: 调用 AKShare 获取原始数据
  2. clean_kline: 中文列名→英文、去重、类型转换、异常过滤
  3. save_kline_to_db: 写入 daily_klines 表
"""

import logging

import akshare as ak
import pandas as pd

from src.data.db import get_db_connection

logger = logging.getLogger(__name__)


class CollectorError(Exception):
    """数据采集异常基类"""
    pass


# AKShare 中文列名 → 系统英文列名映射
_COLUMN_MAP = {
    "日期": "trade_date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "换手率": "turnover",
}

# 必备字段（清洗后必须存在）
_REQUIRED_COLS = {"trade_date", "open", "high", "low", "close", "volume"}


def fetch_daily_kline(
    stock_code: str,
    start: str | None = None,
    end: str | None = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """获取单只股票日K线数据

    Args:
        stock_code: 股票代码（如 "000001.SZ", "600000.SH"）
        start: 起始日期 "YYYY-MM-DD"，默认最近一年
        end: 截止日期 "YYYY-MM-DD"，默认今天
        adjust: 复权方式 ("qfq"前复权, "hfq"后复权, ""不复权)

    Returns:
        pd.DataFrame: 原始 AKShare 返回的 DataFrame

    Raises:
        CollectorError: 网络异常或数据源错误时抛出
    """
    # 格式化日期为 AKShare 要求的 YYYYMMDD
    start_s = start.replace("-", "") if start else None
    end_s = end.replace("-", "") if end else None

    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_s,
            end_date=end_s,
            adjust=adjust,
        )
    except Exception as e:
        raise CollectorError(f"采集失败 {stock_code}: {e}") from e

    if df is None:
        return pd.DataFrame()

    # AKShare 可能返回带 index 的 None-like 结构
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    return df


def clean_kline(raw: pd.DataFrame) -> pd.DataFrame:
    """清洗 AKShare 原始日K线数据

    - 中文列名 → 英文列名
    - 去重（按 trade_date）
    - 日期字符串 → date 对象
    - 保留有用字段，丢弃无关列

    Args:
        raw: AKShare 返回的原始 DataFrame

    Returns:
        pd.DataFrame: 清洗后的数据
    """
    if raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    # 筛选已知的映射列
    known_cols = {c for c in df.columns if c in _COLUMN_MAP}
    if not known_cols:
        # 没有任何可识别列，返回空
        return pd.DataFrame()

    df = df[list(known_cols)].rename(columns=_COLUMN_MAP)

    # 解析日期
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    # 去重
    df = df.drop_duplicates(subset=["trade_date"])

    return df


def save_kline_to_db(df: pd.DataFrame, stock_code: str) -> int:
    """将清洗后的日K线数据写入数据库

    Args:
        df: 清洗后的 DataFrame（含 trade_date, open, high, low, close, volume 等）
        stock_code: 股票代码

    Returns:
        int: 插入行数

    Raises:
        CollectorError: 数据库写入异常
    """
    if df.empty:
        return 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        inserted = 0
        for _, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO daily_klines
                    (stock_code, trade_date, open, high, low, close, volume, amount,
                     amplitude, pct_change, change_value, turnover, adjust_flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    amplitude = EXCLUDED.amplitude,
                    pct_change = EXCLUDED.pct_change,
                    change_value = EXCLUDED.change_value,
                    turnover = EXCLUDED.turnover,
                    adjust_flag = EXCLUDED.adjust_flag
                """,
                (
                    stock_code,
                    row.get("trade_date"),
                    float(row.get("open")) if pd.notna(row.get("open")) else None,
                    float(row.get("high")) if pd.notna(row.get("high")) else None,
                    float(row.get("low")) if pd.notna(row.get("low")) else None,
                    float(row.get("close")) if pd.notna(row.get("close")) else None,
                    float(row.get("volume")) if pd.notna(row.get("volume")) else None,
                    float(row.get("amount")) if pd.notna(row.get("amount")) else None,
                    float(row.get("amplitude")) if pd.notna(row.get("amplitude")) else None,
                    float(row.get("pct_change")) if pd.notna(row.get("pct_change")) else None,
                    float(row.get("change")) if pd.notna(row.get("change")) else None,
                    float(row.get("turnover")) if pd.notna(row.get("turnover")) else None,
                    "qfq",
                ),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("入库 %s: %d 条", stock_code, inserted)
        return inserted

    except Exception as e:
        logger.error("入库失败 %s: %s", stock_code, e)
        raise CollectorError(f"入库失败 {stock_code}: {e}") from e
