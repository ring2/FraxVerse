"""AKShare 板块数据采集器 — 板块信息、成分股、资金流向

P0-2.2: 板块数据采集与入库
  1. fetch_sector_list: 获取全市场板块列表
  2. fetch_sector_constituents: 获取指定板块的成分股
  3. fetch_sector_fund_flow: 获取板块资金流向
  4. save_sector_data_to_db: 板块概况入库
  5. save_sector_fund_flow_to_db: 资金流数据更新入库
"""

import json
import logging
from datetime import date

import akshare as ak
import pandas as pd

from src.data.db import get_db_connection

logger = logging.getLogger(__name__)


class CollectorError(Exception):
    """数据采集异常基类"""
    pass


# ── 板块列表 ──────────────────────────────────────────────────────

_SECTOR_COLUMN_MAP_RAW = {
    "板块名称": "sector_name",
    "板块代码": "sector_code",
}


def fetch_sector_list() -> pd.DataFrame:
    """获取全市场行业板块列表

    Returns:
        pd.DataFrame: 含 sector_code, sector_name 的 DataFrame，失败时返回空
    """
    try:
        df = ak.stock_board_industry_name_em()
    except Exception as e:
        logger.warning("获取板块列表失败: %s", e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    # 提取已知列并重命名
    known = {c for c in df.columns if c in _SECTOR_COLUMN_MAP_RAW}
    result = df[list(known)].rename(columns=_SECTOR_COLUMN_MAP_RAW) if known else pd.DataFrame()
    return result


# ── 板块成分股 ────────────────────────────────────────────────────

_CONS_COLUMN_MAP = {
    "代码": "stock_code",
    "名称": "stock_name",
}


def fetch_sector_constituents(sector_name: str) -> pd.DataFrame:
    """获取指定板块的成分股列表

    Args:
        sector_name: 板块名称，如 "商业航天"

    Returns:
        pd.DataFrame: 含 stock_code, stock_name 的 DataFrame
    """
    try:
        df = ak.stock_board_industry_cons_em(symbol=sector_name)
    except Exception as e:
        logger.warning("获取板块 %s 成分股失败: %s", sector_name, e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    known = {c for c in df.columns if c in _CONS_COLUMN_MAP}
    result = df[list(known)].rename(columns=_CONS_COLUMN_MAP) if known else pd.DataFrame()
    return result


# ── 板块资金流向 ──────────────────────────────────────────────────

_FUND_FLOW_COLUMN_MAP = {
    "日期": "trade_date",
    "行业名称": "sector_name",
    "主力净流入-净额": "main_net_amount",
    "主力净流入-净占比": "main_net_pct",
    "超大单净流入-净额": "super_large_net_amount",
    "超大单净流入-净占比": "super_large_net_pct",
    "大单净流入-净额": "large_net_amount",
    "大单净流入-净占比": "large_net_pct",
    "中单净流入-净额": "medium_net_amount",
    "中单净流入-净占比": "medium_net_pct",
    "小单净流入-净额": "small_net_amount",
    "小单净流入-净占比": "small_net_pct",
}


def fetch_sector_fund_flow(sector_name: str) -> pd.DataFrame:
    """获取指定板块的资金流向历史

    Args:
        sector_name: 板块名称

    Returns:
        pd.DataFrame: 含资金流向数据的 DataFrame
    """
    try:
        df = ak.stock_fund_flow_industry(symbol=sector_name)
    except Exception as e:
        logger.warning("获取板块 %s 资金流向失败: %s", sector_name, e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    known = {c for c in df.columns if c in _FUND_FLOW_COLUMN_MAP}
    if not known:
        return pd.DataFrame()

    result = df[list(known)].rename(columns=_FUND_FLOW_COLUMN_MAP)

    # 日期处理
    if "trade_date" in result.columns:
        result["trade_date"] = pd.to_datetime(result["trade_date"]).dt.date

    # 数值类型转换
    for col in result.columns:
        if col in ("trade_date", "sector_name"):
            continue
        result[col] = pd.to_numeric(result[col], errors="coerce")

    return result


# ── 入库 ─────────────────────────────────────────────────────────

def save_sector_data_to_db(
    df: pd.DataFrame,
    trade_date: date,
    sector_type: str = "industry",
) -> int:
    """将板块概况数据写入 sector_data 表

    Args:
        df: 含 sector_code, sector_name 等字段的 DataFrame
        trade_date: 交易日期
        sector_type: 板块类型（industry/concept/region）

    Returns:
        int: 插入/更新行数
    """
    if df.empty:
        return 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        inserted = 0
        for _, row in df.iterrows():
            leader_str = row.get("leader_stocks")
            leader_json = json.dumps(leader_str) if isinstance(leader_str, list) else "[]"

            cursor.execute(
                """
                INSERT INTO sector_data
                    (sector_code, sector_name, sector_type, trade_date,
                     capital_ratio, change_pct, leader_stocks)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (sector_code, trade_date) DO UPDATE SET
                    sector_name = EXCLUDED.sector_name,
                    capital_ratio = EXCLUDED.capital_ratio,
                    change_pct = EXCLUDED.change_pct,
                    leader_stocks = EXCLUDED.leader_stocks
                """,
                (
                    row.get("sector_code"),
                    row.get("sector_name"),
                    sector_type,
                    trade_date,
                    float(row["capital_ratio"]) if pd.notna(row.get("capital_ratio")) else None,
                    float(row["change_pct"]) if pd.notna(row.get("change_pct")) else None,
                    leader_json,
                ),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("板块数据入库: %d 条", inserted)
        return inserted

    except Exception as e:
        logger.error("板块数据入库失败: %s", e)
        raise CollectorError(f"板块数据入库失败: {e}") from e


def save_sector_fund_flow_to_db(df: pd.DataFrame) -> int:
    """将板块资金流向数据更新到 sector_data 表

    按 sector_name + trade_date 匹配，更新资金流向相关字段。
    sector_data 表中没有独立的资金流字段，这里复用 capital_ratio 和 change_pct。

    Args:
        df: 含 sector_name, trade_date, main_net_amount 等字段的 DataFrame

    Returns:
        int: 更新行数
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
                INSERT INTO sector_data
                    (sector_code, sector_name, sector_type, trade_date,
                     capital_ratio, change_pct)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (sector_code, trade_date) DO UPDATE SET
                    capital_ratio = EXCLUDED.capital_ratio,
                    change_pct = EXCLUDED.change_pct
                """,
                (
                    row.get("sector_code", ""),
                    row.get("sector_name"),
                    "industry",
                    row["trade_date"],
                    float(row["main_net_pct"]) if pd.notna(row.get("main_net_pct")) else None,
                    float(row["change_pct"]) if pd.notna(row.get("change_pct")) else None,
                ),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("板块资金流入库: %d 条", inserted)
        return inserted

    except Exception as e:
        logger.error("板块资金流入库失败: %s", e)
        raise CollectorError(f"板块资金流入库失败: {e}") from e
