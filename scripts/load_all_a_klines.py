#!/usr/bin/env python3
"""全 A 股灌入 2026 年 K 线数据

用法：
    docker exec -i fraxverse-scheduler sh -c "cat > /app/load_all_a_klines.py"
    docker exec fraxverse-scheduler python /app/load_all_a_klines.py --year 2026
    docker exec fraxverse-scheduler python /app/load_all_a_klines.py --year 2026 --batch 500  # 限500只
"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "fraxverse",
    "user": "fraxverse",
    "password": "fraxverse_dev",
}


def get_db():
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def fetch_all_a_stocks() -> list[dict]:
    """从 AKShare 获取全 A 股列表（~5,300 只）"""
    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        logger.error("AKShare 返回空股票列表")
        return []

    # AKShare 字段名可能有变化
    code_col = None
    name_col = None
    for col in df.columns:
        if '代码' in col:
            code_col = col
        if '名称' in col:
            name_col = col

    if not code_col or not name_col:
        logger.error(f"未找到代码/名列，现有列: {df.columns.tolist()}")
        return []

    stocks = []
    for _, row in df.iterrows():
        code = str(row[code_col]).strip()
        name = str(row[name_col]).strip()

        # 判断市场
        if code.startswith('6') or code.startswith('9'):
            market = 'SH'
        elif code.startswith('0') or code.startswith('3') or code.startswith('2'):
            market = 'SZ'
        elif code.startswith('4') or code.startswith('8'):
            market = 'BJ'
        else:
            market = 'A'

        full_code = f"{code}.{market}" if market != 'A' else code
        stocks.append({"code": full_code, "name": name, "symbol": code, "market": market})

    logger.info(f"获取全 A 股列表: {len(stocks)} 只")
    return stocks


def ensure_stock(code: str, name: str, market: str):
    """确保 stocks 表有这条记录"""
    import psycopg2
    try:
        conn = get_db()
        cur = conn.cursor()
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
        logger.warning(f"ensure_stock({code}) failed: {e}")


def check_existing(stock_codes: list[str], year: int) -> set[str]:
    """检查已存在的K线数据，返回已有足够数据的代码集合"""
    import psycopg2
    if not stock_codes:
        return set()

    conn = get_db()
    cur = conn.cursor()
    # 估算一年约 245 个交易日，有 200 条以上视为已灌
    placeholders = ",".join(["%s"] * len(stock_codes))
    cur.execute(
        f"""
        SELECT stock_code, COUNT(*)
        FROM daily_klines
        WHERE stock_code IN ({placeholders})
          AND trade_date >= %s AND trade_date <= %s
        GROUP BY stock_code
        HAVING COUNT(*) >= 200
        """,
        stock_codes + [date(year, 1, 1), date(year, 12, 31)],
    )
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    logger.info(f"已有足够数据的标的: {len(existing)} 只")
    return existing


def fetch_and_save_stock(symbol: str, full_code: str, name: str, market: str,
                         year: int, delay: float) -> tuple[str, int, str]:
    """拉取并保存单只股票的年K线"""
    import psycopg2

    ensure_stock(full_code, name, market)

    try:
        import akshare as ak
        start_str = f"{year}-01-01"
        end_str = f"{year}-12-31"

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_str.replace("-", ""),
            end_date=end_str.replace("-", ""),
            adjust="qfq",
        )

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return (full_code, 0, "无数据")

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
        if not known:
            return (full_code, 0, "列名不匹配")

        df = df[list(known.keys())].rename(columns=known)
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

        # 批量写入 DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        inserted = 0
        for _, row in df.iterrows():
            cur.execute(
                "DELETE FROM daily_klines WHERE stock_code=%s AND trade_date=%s AND adjust_flag='qfq'",
                (full_code, row.get("trade_date")),
            )
            cur.execute(
                """
                INSERT INTO daily_klines
                    (stock_code, trade_date, open, high, low, close, volume, amount,
                     turnover_rate, adjust_flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    full_code,
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

        if delay > 0:
            time.sleep(delay)

        return (full_code, inserted, "成功")

    except Exception as e:
        msg = str(e)[:80]
        return (full_code, 0, f"失败: {msg}")


def main():
    parser = argparse.ArgumentParser(description="全 A 股灌入年K线")
    parser.add_argument("--year", type=int, default=2026, help="年份")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔(秒)")
    parser.add_argument("--batch", type=int, default=0, help="限制数量(0=全部)")
    parser.add_argument("--workers", type=int, default=2, help="并发数")
    parser.add_argument("--list-only", action="store_true", help="仅拉取股票列表，不拉K线")
    args = parser.parse_args()

    print(f"\n🚀 全 A 股 K 线灌入")
    print(f"   年份: {args.year}")
    print(f"   间隔: {args.delay}s")
    print(f"   并发: {args.workers}\n")

    # 获取全 A 股列表
    all_stocks = fetch_all_a_stocks()
    if not all_stocks:
        print("❌ 无法获取 A 股列表")
        sys.exit(1)

    if args.list_only:
        print(f"\n共 {len(all_stocks)} 只标的")
        print(f"示例前10只:")
        for s in all_stocks[:10]:
            print(f"  {s['code']} {s['name']} ({s['market']})")
        return

    # 过滤掉已有的
    codes = [s["code"] for s in all_stocks]
    existing = check_existing(codes, args.year)

    to_fetch = [s for s in all_stocks if s["code"] not in existing]
    logger.info(f"需拉取: {len(to_fetch)} 只 (已有 {len(existing)} 只)")

    if args.batch > 0:
        to_fetch = to_fetch[:args.batch]

    if not to_fetch:
        print("所有标的数据已存在，无需拉取")
        return

    total_inserted = 0
    success = 0
    failed = 0

    start_time = time.time()

    # 顺序执行（AKShare 限流，并发容易出错）
    for i, stock in enumerate(to_fetch, 1):
        code, cnt, status = fetch_and_save_stock(
            stock["symbol"], stock["code"], stock["name"],
            stock["market"], args.year, args.delay,
        )

        total_inserted += cnt
        if cnt > 0:
            success += 1
            logger.info(f"[{i}/{len(to_fetch)}] {code} {stock['name']}: {cnt} 条 ✅")
        else:
            failed += 1
            if i <= 3:  # 前几只打印详情
                logger.warning(f"[{i}/{len(to_fetch)}] {code} {stock['name']}: {status}")

        # 每 200 只打印进度摘要
        if i % 200 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60
            logger.info(f"--- 进度: {i}/{len(to_fetch)} ({i/len(to_fetch)*100:.0f}%), "
                        f"已插入 {total_inserted} 行, "
                        f"{rate:.0f} 只/分钟 ---")

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"📊 灌入完成!")
    print(f"   年份:   {args.year}")
    print(f"   总量:   {len(to_fetch)} 只")
    print(f"   成功:   {success}")
    print(f"   失败:   {failed}")
    print(f"   插入行: {total_inserted}")
    print(f"   耗时:   {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"   速度:   {len(to_fetch)/(elapsed/60):.0f} 只/分钟")

    # 最终统计
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM daily_klines WHERE trade_date >= '{args.year}-01-01' AND trade_date <= '{args.year}-12-31'")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(DISTINCT stock_code) FROM daily_klines WHERE trade_date >= '{args.year}-01-01' AND trade_date <= '{args.year}-12-31'")
    stocks_with_data = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"\n   库中总计: {total} 条K线, {stocks_with_data} 只标的")


if __name__ == "__main__":
    main()
