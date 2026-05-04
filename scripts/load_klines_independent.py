#!/usr/bin/env python3
"""灌入历史 K 线数据 — 独立版本（不依赖 collector.py）

用法：
    python scripts/load_klines_independent.py
"""

import logging
import sys
import time
from datetime import date, datetime

import pandas as pd

sys.path.insert(0, "/home/ubuntu/FraxVerse")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── 直连 DB ───────────────────────────────────────
import psycopg2

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "fraxverse",
    "user": "fraxverse",
    "password": "fraxverse_dev",
}

# ── 关注标的 ─────────────────────────────────────
STOCKS = [
    ("000001.SZ", "平安银行"),
    ("000002.SZ", "万科A"),
    ("000333.SZ", "美的集团"),
    ("000568.SZ", "泸州老窖"),
    ("000630.SZ", "铜陵有色"),
    ("000858.SZ", "五粮液"),
    ("002129.SZ", "TCL中环"),
    ("002304.SZ", "洋河股份"),
    ("002415.SZ", "海康威视"),
    ("002594.SZ", "比亚迪"),
    ("300274.SZ", "阳光电源"),
    ("300750.SZ", "宁德时代"),
    ("600028.SH", "中国石化"),
    ("600030.SH", "中信证券"),
    ("600036.SH", "招商银行"),
    ("600276.SH", "恒瑞医药"),
    ("600519.SH", "贵州茅台"),
    ("600585.SH", "海螺水泥"),
    ("600900.SH", "长江电力"),
    ("600941.SH", "中国移动"),
    ("601012.SH", "隆基绿能"),
    ("601166.SH", "兴业银行"),
    ("601318.SH", "中国平安"),
    ("601728.SH", "中国电信"),
    ("601857.SH", "中国石油"),
    ("601899.SH", "紫金矿业"),
]


def ensure_stock(code: str, name: str):
    """确保 stocks 表有这条记录"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        market = "SZ" if code.endswith("SZ") else "SH"
        cur.execute(
            "INSERT INTO stocks (code, name, market, is_st, is_suspended) "
            "VALUES (%s, %s, %s, false, false) "
            "ON CONFLICT (code) DO NOTHING",
            (code, name, market),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning("ensure_stock(%s) failed: %s", code, e)


def fetch_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    """从 AKShare 拉历史数据"""
    import akshare as ak

    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start.replace("-", ""),
        end_date=end.replace("-", ""),
        adjust="qfq",
    )
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    # 重命名中文列名
    col_map = {
        "日期": "trade_date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "换手率": "turnover",
    }
    known = {c: col_map[c] for c in df.columns if c in col_map}
    df = df[list(known.keys())].rename(columns=known)
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    return df


def save_to_db(df: pd.DataFrame, stock_code: str) -> int:
    """写入 daily_klines 表"""
    if df.empty:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    inserted = 0

    for _, row in df.iterrows():
        # 先删已存在（唯一约束含 adjust_flag）
        cur.execute(
            "DELETE FROM daily_klines WHERE stock_code=%s AND trade_date=%s AND adjust_flag='qfq'",
            (stock_code, row.get("trade_date")),
        )
        cur.execute(
            """
            INSERT INTO daily_klines
                (stock_code, trade_date, open, high, low, close, volume, amount,
                 turnover_rate, adjust_flag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                stock_code,
                row.get("trade_date"),
                float(row["open"]) if pd.notna(row.get("open")) else None,
                float(row["high"]) if pd.notna(row.get("high")) else None,
                float(row["low"]) if pd.notna(row.get("low")) else None,
                float(row["close"]) if pd.notna(row.get("close")) else None,
                float(row["volume"]) if pd.notna(row.get("volume")) else None,
                float(row["amount"]) if pd.notna(row.get("amount")) else None,
                float(row["turnover"]) if pd.notna(row.get("turnover")) else None,
                "qfq",
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    return inserted


def main():
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    print(f"\n🚀 历史K线灌入 — 独立版")
    print(f"   区间: {start_date} → {end_date}")
    print(f"   标的: {len(STOCKS)} 只\n")

    total = 0
    success = 0
    failed = 0

    for i, (code, name) in enumerate(STOCKS, 1):
        ensure_stock(code, name)

        # AKShare 只需纯数字代码
        symbol = code.split(".")[0]
        try:
            df = fetch_history(symbol, start_date, end_date)
            if df.empty:
                logger.warning("[%d/%d] %s %s: 无数据", i, len(STOCKS), code, name)
                failed += 1
                time.sleep(0.5)
                continue

            count = save_to_db(df, code)
            if count > 0:
                logger.info(
                    "[%d/%d] %s %s: 插入 %d 条 ✅ (%s → %s)",
                    i, len(STOCKS), code, name, count,
                    df["trade_date"].iloc[0], df["trade_date"].iloc[-1],
                )
                total += count
                success += 1
            else:
                logger.warning("[%d/%d] %s %s: 无数据", i, len(STOCKS), code, name)
                failed += 1
        except Exception as e:
            logger.error("[%d/%d] %s %s: 失败 - %s", i, len(STOCKS), code, name, e)
            failed += 1

        time.sleep(1.0)  # AKShare 限流

    print(f"\n📊 完成!")
    print(f"   成功: {success}, 失败: {failed}, 总K线: {total}")


if __name__ == "__main__":
    main()
