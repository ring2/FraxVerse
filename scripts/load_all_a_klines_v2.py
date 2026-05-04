#!/usr/bin/env python3
"""全 A 股灌入 2026 年 K 线数据 — V2: 先存列表文件，再批量拉取

用法：
    # 第一步：获取全 A 股列表（只需跑一次）
    docker exec fraxverse-scheduler python /app/load_all_a_klines_v2.py --list-only

    # 第二步：批量灌入（后台运行）
    nohup docker exec fraxverse-scheduler python /app/load_all_a_klines_v2.py --year 2026 --delay 0.3 &

    # 第三步：检查进度
    docker exec fraxverse-scheduler python /app/load_all_a_klines_v2.py --stats
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date

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

LIST_FILE = "/app/data/a_stock_list.json"


def get_db():
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)


def fetch_and_save_list():
    """从 AKShare 获取全 A 股列表并保存到文件"""
    import akshare as ak

    print("正在从 AKShare 拉取全 A 股列表...")
    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        print("❌ 无法获取股票列表")
        return []

    code_col = None
    name_col = None
    for col in df.columns:
        if '代码' in col:
            code_col = col
        if '名称' in col:
            name_col = col

    if not code_col or not name_col:
        print(f"❌ 未找到代码/名列，现有列: {df.columns.tolist()}")
        return []

    stocks = []
    for _, row in df.iterrows():
        code = str(row[code_col]).strip()
        name = str(row[name_col]).strip()

        if code.startswith('6') or code.startswith('9'):
            market = 'SH'
        elif code.startswith('0') or code.startswith('3') or code.startswith('2'):
            market = 'SZ'
        elif code.startswith('4') or code.startswith('8'):
            market = 'BJ'
        else:
            market = 'A'

        full_code = f"{code}.{market}"
        stocks.append({"code": full_code, "symbol": code, "name": name, "market": market})

    # 保存到文件
    os.makedirs(os.path.dirname(LIST_FILE), exist_ok=True)
    with open(LIST_FILE, "w") as f:
        json.dump(stocks, f, ensure_ascii=False)

    print(f"✅ 已保存 {len(stocks)} 只标的到 {LIST_FILE}")
    return stocks


def load_stock_list() -> list[dict]:
    """从文件加载股票列表"""
    if not os.path.exists(LIST_FILE):
        print(f"❌ 列表文件不存在: {LIST_FILE}")
        print(f"   请先运行: --list-only")
        return []
    with open(LIST_FILE) as f:
        return json.load(f)


def check_existing(year: int) -> set[str]:
    """检查哪些标的已有足够的 K 线数据"""
    import psycopg2

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT stock_code
        FROM daily_klines
        WHERE trade_date >= %s AND trade_date <= %s
        GROUP BY stock_code
        HAVING COUNT(*) >= 200
        """,
        (date(year, 1, 1), date(year, 12, 31)),
    )
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    return existing


def get_total_stats(year: int) -> dict:
    """获取灌入统计"""
    import psycopg2
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM daily_klines "
        f"WHERE trade_date >= '{year}-01-01' AND trade_date <= '{year}-12-31'"
    )
    total, distinct = cur.fetchone()
    cur.close()
    conn.close()
    return {"total_klines": total, "distinct_stocks": distinct}


def main():
    parser = argparse.ArgumentParser(description="全 A 股灌入年K线 V2")
    parser.add_argument("--year", type=int, default=2026, help="年份")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔(秒)")
    parser.add_argument("--batch", type=int, default=0, help="限制拉取数量(0=全部)")
    parser.add_argument("--list-only", action="store_true", help="仅拉取并保存股票列表")
    parser.add_argument("--stats", action="store_true", help="查看灌入进度统计")
    parser.add_argument("--resume", action="store_true", help="续传：跳过已灌标的")
    args = parser.parse_args()

    if args.list_only:
        fetch_and_save_list()
        return

    if args.stats:
        stats = get_total_stats(args.year)
        all_stocks = load_stock_list()
        total_stocks = len(all_stocks) if all_stocks else 0
        pct = stats["distinct_stocks"] / total_stocks * 100 if total_stocks > 0 else 0
        print(f"📊 灌入进度 ({args.year})")
        print(f"   标的: {stats['distinct_stocks']} / {total_stocks} ({pct:.1f}%)")
        print(f"   K线: {stats['total_klines']} 条")
        print(f"   预计还需: {(total_stocks - stats['distinct_stocks']) / 100:.0f} 分钟")
        return

    # 加载股票列表
    all_stocks = load_stock_list()
    if not all_stocks:
        return

    # 过滤已有的
    to_fetch = all_stocks.copy()
    if args.resume:
        existing = check_existing(args.year)
        to_fetch = [s for s in all_stocks if s["code"] not in existing]
        logger.info(f"续传模式: 需拉取 {len(to_fetch)} 只 (已有 {len(existing)} 只)")

    if args.batch > 0:
        to_fetch = to_fetch[:args.batch]

    logger.info(f"开始拉取 {len(to_fetch)} 只标的...")

    total_inserted = 0
    success = 0
    failed = 0
    start_time = time.time()

    for i, stock in enumerate(to_fetch, 1):
        code = stock["code"]
        symbol = stock["symbol"]
        name = stock["name"]
        market = stock["market"]

        # 确保 stocks 表有记录
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
            pass

        try:
            import akshare as ak
            start_str = f"{args.year}-01-01"
            end_str = f"{args.year}-12-31"

            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_str.replace("-", ""),
                end_date=end_str.replace("-", ""),
                adjust="qfq",
            )

            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                failed += 1
                if i <= 5:
                    logger.warning(f"[{i}/{len(to_fetch)}] {code} {name}: 无数据")
                continue

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
                failed += 1
                continue

            df = df[list(known.keys())].rename(columns=known)
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

            # 批量写入
            conn2 = get_db()
            cur2 = conn2.cursor()
            inserted = 0
            for _, row in df.iterrows():
                cur2.execute(
                    "DELETE FROM daily_klines WHERE stock_code=%s AND trade_date=%s AND adjust_flag='qfq'",
                    (code, row.get("trade_date")),
                )
                cur2.execute(
                    """
                    INSERT INTO daily_klines
                        (stock_code, trade_date, open, high, low, close, volume, amount,
                         turnover_rate, adjust_flag)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        code,
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

            conn2.commit()
            cur2.close()
            conn2.close()

            total_inserted += inserted
            if inserted > 0:
                success += 1
                if success % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = success / elapsed * 60
                    remaining = len(to_fetch) - i
                    eta = remaining / (rate / 60) if rate > 0 else 0
                    logger.info(
                        f"[{i}/{len(to_fetch)}] ✅ {success}只成功 / {failed}只失败 | "
                        f"已插入 {total_inserted} 行 | {rate:.0f}只/分 | 预计剩余 {eta:.0f}分"
                    )
            else:
                failed += 1

            if args.delay > 0:
                time.sleep(args.delay)

        except Exception as e:
            failed += 1
            if i <= 5 or failed % 100 == 0:
                logger.warning(f"[{i}/{len(to_fetch)}] {code} {name}: {str(e)[:60]}")

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"📊 灌入完成!")
    print(f"   年份:   {args.year}")
    print(f"   总量:   {len(to_fetch)} 只")
    print(f"   成功:   {success}")
    print(f"   失败:   {failed}")
    print(f"   插入行: {total_inserted}")
    print(f"   耗时:   {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"   速度:   {success/(elapsed/60):.0f} 只/分钟" if elapsed > 0 else "   速度:   N/A")

    stats = get_total_stats(args.year)
    print(f"\n   库中总计: {stats['total_klines']} 条K线, {stats['distinct_stocks']} 只标的")


if __name__ == "__main__":
    main()
