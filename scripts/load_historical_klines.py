#!/usr/bin/env python3
"""灌入历史 K 线数据到 daily_klines 表

用法：
    python scripts/load_historical_klines.py                  # 拉 stock_pool 涉及标的
    python scripts/load_historical_klines.py --all-stocks      # 拉全市场（慢）
    python scripts/load_historical_klines.py --start 2024-01-01 --end 2024-12-31
"""

import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta

import pandas as pd

sys.path.insert(0, "/home/ubuntu/FraxVerse")

from src.data.collector import fetch_daily_kline, clean_kline, save_kline_to_db
from src.data.db import get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_START = "2024-01-01"
DEFAULT_END = "2024-12-31"


def get_focus_stocks() -> list[dict]:
    """从 stock_pool + stocks 表获取关注标的列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT sp.stock_code, COALESCE(s.name, '未知')
        FROM stock_pool sp
        LEFT JOIN stocks s ON sp.stock_code = s.code
        ORDER BY sp.stock_code
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    logger.info("从 stock_pool 获取 %d 只关注标的", len(rows))
    return [{"code": r[0], "name": r[1]} for r in rows]


def get_all_stocks() -> list[dict]:
    """从 stocks 表获取所有已入库股票"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name FROM stocks WHERE is_suspended = false ORDER BY code")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    logger.info("从 stocks 表获取 %d 只股票", len(rows))
    return [{"code": r[0], "name": r[1]} for r in rows]


def check_existing_klines(stock_codes: list[str]) -> dict[str, int]:
    """检查哪些标的已有 K 线数据"""
    if not stock_codes:
        return {}

    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ",".join(["%s"] * len(stock_codes))
    cursor.execute(
        f"""
        SELECT stock_code, COUNT(*)
        FROM daily_klines
        WHERE stock_code IN ({placeholders})
        GROUP BY stock_code
        """,
        stock_codes,
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {r[0]: r[1] for r in rows}


def ensure_stock_in_table(code: str, name: str, market: str) -> bool:
    """确保股票在 stocks 表中存在，不存在则插入"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stocks (code, name, market, is_st, is_suspended) "
            "VALUES (%s, %s, %s, false, false) "
            "ON CONFLICT (code) DO NOTHING",
            (code, name, market),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        logger.warning("插入 stocks 表失败 %s: %s", code, e)
        return False
    finally:
        cursor.close()
        conn.close()


def load_history_for_stock(
    stock: dict,
    start: str,
    end: str,
    delay: float = 1.0,
) -> int:
    """拉取并入库单只股票的历史K线"""
    code = stock["code"]
    name = stock.get("name", "")
    market = "SZ" if code.endswith("SZ") else "SH"

    try:
        # 确保 stocks 表存在
        ensure_stock_in_table(code, name, market)

        # AKShare 需要纯数字代码（去掉 .SZ/.SH 后缀）
        akshare_code = code.split(".")[0]
        raw = fetch_daily_kline(akshare_code, start=start, end=end, adjust="qfq")
        if raw.empty:
            logger.warning("%s (%s): 无数据", code, name)
            return 0

        cleaned = clean_kline(raw)
        if cleaned.empty:
            logger.warning("%s (%s): 清洗后无数据", code, name)
            return 0

        count = save_kline_to_db(cleaned, code)
        if count > 0 and delay > 0:
            time.sleep(delay)  # AKShare 限流
        return count

    except Exception as e:
        logger.error("%s (%s): 采集失败 - %s", code, name, e)
        if delay > 0:
            time.sleep(delay * 2)
        return 0


def main():
    parser = argparse.ArgumentParser(description="灌入历史K线数据")
    parser.add_argument("--start", default=DEFAULT_START, help="开始日期")
    parser.add_argument("--end", default=DEFAULT_END, help="结束日期")
    parser.add_argument("--all-stocks", action="store_true", help="拉全市场股票（默认只拉关注标的）")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数（防限流）")
    parser.add_argument("--limit", type=int, default=0, help="最多拉取标的数（0=不限制）")
    parser.add_argument("--check-only", action="store_true", help="仅检查已有数据，不拉取")
    args = parser.parse_args()

    start_date = args.start
    end_date = args.end

    print(f"\n🚀 历史K线数据灌入")
    print(f"   区间: {start_date} → {end_date}")
    print(f"   间隔: {args.delay}s\n")

    # 确定要拉取的标的列表
    if args.all_stocks:
        stocks = get_all_stocks()
    else:
        stocks = get_focus_stocks()

    if not stocks:
        print("❌ 没有找到任何标的，请先确认 stocks / stock_pool 表有数据")
        sys.exit(1)

    # 检查已有数据
    codes = [s["code"] for s in stocks]
    existing = check_existing_klines(codes)

    if args.check_only:
        print(f"\n{'代码':<12} {'名称':<10} {'已有K线':>8}")
        print("-" * 32)
        total = 0
        for s in stocks:
            cnt = existing.get(s["code"], 0)
            total += cnt
            print(f"{s['code']:<12} {s['name']:<10} {cnt:>8}")
        print(f"\n总计: {len(stocks)} 只标的, {total} 条K线")
        return

    if args.limit > 0:
        stocks = stocks[:args.limit]

    # 批量拉取
    print(f"\n开始拉取 {len(stocks)} 只标的...")
    print("=" * 50)

    total_inserted = 0
    success = 0
    failed = 0
    skipped = 0

    start_time = time.time()

    for i, stock in enumerate(stocks, 1):
        code = stock["code"]
        existing_count = existing.get(code, 0)

        # 如果已有足够数据（>200条≈全年），跳过
        if existing_count >= 200:
            logger.info("[%d/%d] %s (%s) 已有 %d 条，跳过", i, len(stocks), code, stock.get("name", ""), existing_count)
            skipped += 1
            continue

        count = load_history_for_stock(stock, start_date, end_date, delay=args.delay)

        if count > 0:
            total_inserted += count
            success += 1
            action = "更新" if existing_count > 0 else "新增"
            logger.info("[%d/%d] %s (%s) %s %d 条 ✅", i, len(stocks), code, stock.get("name", ""), action, count)
        else:
            failed += 1
            logger.warning("[%d/%d] %s (%s) 无数据 ⚠️", i, len(stocks), code, stock.get("name", ""))

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"📊 灌入完成!")
    print(f"   总标的:  {len(stocks)}")
    print(f"   成功:    {success}")
    print(f"   跳过:    {skipped}")
    print(f"   失败:    {failed}")
    print(f"   插入行:  {total_inserted}")
    print(f"   耗时:    {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # 检查最终结果
    codes2 = [s["code"] for s in stocks]
    final = check_existing_klines(codes2)
    total_final = sum(final.values())
    print(f"\n   库中总计: {total_final} 条K线")


if __name__ == "__main__":
    main()
