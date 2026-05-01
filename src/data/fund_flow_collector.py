"""AKShare 个股资金流向采集器

P0-2.3: 个股资金流向 + 大单/小单分布
  1. fetch_individual_fund_flow: 个股资金流向原始数据
  2. clean_fund_flow: 列名映射、口径折算
  3. save_fund_flow_to_db: 写入 fund_flows 表
"""

import logging

import akshare as ak
import pandas as pd

from src.data.db import get_db_connection

logger = logging.getLogger(__name__)


class CollectorError(Exception):
    """数据采集异常基类"""
    pass


# 个股资金流向列映射
_FUND_FLOW_COLUMN_MAP = {
    "日期": "trade_date",
    "股票代码": "stock_code",
    "最新价": "price",
    "涨跌幅": "pct_change",
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

# 中小单可能是一个合并列（AKShare 不同版本差异）
_FUND_FLOW_EXTRA_MAP = {
    "中小单净流入-净额": "small_net_amount",
    "中小单净流入-净占比": "small_net_pct",
}


def fetch_individual_fund_flow(stock: str, market: str = "sh") -> pd.DataFrame:
    """获取个股资金流向

    Args:
        stock: 股票代码（支持 000001 或 000001.SZ 格式）
        market: 市场标识（默认 sh，仅当 stock 为纯数字时生效）

    Returns:
        pd.DataFrame: 原始 AKShare 返回的 DataFrame
    """
    # 截断市场后缀
    code = stock.split(".", maxsplit=1)[0]

    try:
        df = ak.stock_individual_fund_flow(stock=code, market=market)
    except Exception as e:
        logger.warning("获取 %s 资金流向失败: %s", stock, e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    return df


def clean_fund_flow(raw: pd.DataFrame) -> pd.DataFrame:
    """清洗个股资金流向数据

    - 中文列名 → 英文列名
    - 日期字符串 → date 对象
    - 数值类型转换
    - 计算 large_order_pct（超大单+大单）
    - 计算 small_order_pct（小单/中小单）

    Args:
        raw: AKShare 返回的原始 DataFrame

    Returns:
        pd.DataFrame: 清洗后的数据
    """
    if raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    # 合并主映射和额外映射
    col_map = {**_FUND_FLOW_COLUMN_MAP, **_FUND_FLOW_EXTRA_MAP}
    known_cols = {c for c in df.columns if c in col_map}
    if not known_cols:
        return pd.DataFrame()

    df = df[list(known_cols)].rename(columns=col_map)

    # 日期解析
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    # 数值转换
    for col in df.columns:
        if col in ("trade_date", "stock_code"):
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 口径折算：large_order_pct = 超大单 + 大单
    if "super_large_net_pct" in df.columns and "large_net_pct" in df.columns:
        df["large_order_pct"] = df["super_large_net_pct"] + df["large_net_pct"]
    elif "large_net_pct" in df.columns:
        df["large_order_pct"] = df["large_net_pct"]

    # small_order_pct：有中小单就用中小单，否则用小单
    if "small_net_pct" in df.columns:
        df["small_order_pct"] = df["small_net_pct"]

    return df


def save_fund_flow_to_db(df: pd.DataFrame, stock_code: str) -> int:
    """将清洗后的资金流向数据写入 fund_flows 表

    Args:
        df: 清洗后的 DataFrame
        stock_code: 股票代码（含市场后缀）

    Returns:
        int: 插入行数
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
                INSERT INTO fund_flows
                    (stock_code, trade_date, net_amount, main_amount,
                     large_order_pct, small_order_pct, cmf)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                    net_amount = EXCLUDED.net_amount,
                    main_amount = EXCLUDED.main_amount,
                    large_order_pct = EXCLUDED.large_order_pct,
                    small_order_pct = EXCLUDED.small_order_pct,
                    cmf = EXCLUDED.cmf
                """,
                (
                    stock_code,
                    row.get("trade_date"),
                    float(row["main_net_amount"]) if pd.notna(row.get("main_net_amount")) else None,
                    float(row["main_net_amount"]) if pd.notna(row.get("main_net_amount")) else None,
                    float(row["large_order_pct"]) if pd.notna(row.get("large_order_pct")) else None,
                    float(row["small_order_pct"]) if pd.notna(row.get("small_order_pct")) else None,
                    None,  # cmf 后续计算，暂为 None
                ),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("资金流入库 %s: %d 条", stock_code, inserted)
        return inserted

    except Exception as e:
        logger.error("资金流入库失败 %s: %s", stock_code, e)
        raise CollectorError(f"资金流入库失败 {stock_code}: {e}") from e
