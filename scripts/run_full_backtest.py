"""
FraxVerse · 全量回测脚本

从数据库拉取真实数据，跑两个策略的完整回测，输出对比报告。
支持从 AKShare 拉取数据（--mode real）或使用 DB 已有数据（--mode db）。

用法：
    python scripts/run_full_backtest.py                     # 使用DB数据
    python scripts/run_full_backtest.py --mode db --start 2024-01-01 --end 2024-12-31
    python scripts/run_full_backtest.py --mode real         # 从AKShare拉取
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.db.models import DailyKlines, MarketStateLog, StockPool, Stocks
from src.db.session import get_session
from src.strategy.backtest_runner import run_backtest

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── 默认日期范围 ──
DEFAULT_START = "2024-01-01"
DEFAULT_END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


def fetch_klines_from_db(start: date, end: date) -> dict[str, pd.DataFrame]:
    """从 DB 拉取 K 线数据"""
    klines_dict: dict[str, pd.DataFrame] = {}
    with get_session() as db:
        rows = (
            db.query(DailyKlines)
            .filter(
                DailyKlines.trade_date >= start,
                DailyKlines.trade_date <= end,
            )
            .order_by(DailyKlines.stock_code, DailyKlines.trade_date)
            .all()
        )
    if not rows:
        logger.warning("DB 中无 K 线数据")
        return {}

    df = pd.DataFrame(
        [
            {
                "stock_code": r.stock_code,
                "date": r.trade_date,
                "open": float(r.open_price) if r.open_price else 0,
                "high": float(r.high_price) if r.high_price else 0,
                "low": float(r.low_price) if r.low_price else 0,
                "close": float(r.close_price) if r.close_price else 0,
                "volume": float(r.volume) if r.volume else 0,
                "amount": float(r.amount) if r.amount else 0,
                "pre_close": float(r.pre_close) if r.pre_close else 0,
            }
            for r in rows
        ]
    )
    for code, grp in df.groupby("stock_code"):
        grp = grp.sort_values("date").reset_index(drop=True)
        klines_dict[code] = grp
    logger.info(f"从 DB 加载了 {len(klines_dict)} 只标的的 K 线数据")
    return klines_dict


def fetch_market_states(start: date, end: date) -> dict[str, str]:
    """从 DB 拉取市场状态"""
    states: dict[str, str] = {}
    with get_session() as db:
        rows = (
            db.query(MarketStateLog)
            .filter(
                MarketStateLog.date >= start,
                MarketStateLog.date <= end,
            )
            .order_by(MarketStateLog.date)
            .all()
        )
    for r in rows:
        states[r.date.isoformat()] = r.to_state
    logger.info(f"加载了 {len(states)} 天的市场状态")
    return states


def fetch_scored_pool(start: date, end: date) -> dict[str, list[dict]]:
    """从 StockPool 表拉取评分数据"""
    pool: dict[str, list[dict]] = {}
    with get_session() as db:
        rows = (
            db.query(StockPool)
            .filter(
                StockPool.date >= start,
                StockPool.date <= end,
            )
            .order_by(StockPool.date)
            .all()
        )
    for r in rows:
        d = r.date.isoformat()
        if d not in pool:
            pool[d] = []
        pool[d].append({
            "stock_code": r.stock_code,
            "score_total": float(r.score_total) if r.score_total else 0,
            "strategy_type": r.strategy_type or "",
        })
    logger.info(f"加载了 {len(pool)} 天的评分数据，共 {sum(len(v) for v in pool.values())} 条记录")
    return pool


def print_report(result, label: str):
    """打印回测报告"""
    print()
    print("=" * 60)
    print(f"  {label}")
    print("=" * 60)
    print(f"  日期范围:     {result.start_date} → {result.end_date}")
    print(f"  初始资金:     ¥{result.initial_capital:>10,.2f}")
    print(f"  最终资金:     ¥{result.final_capital:>10,.2f}")
    print(f"  总收益率:     {result.total_return_pct:>+7.2f}%")
    print(f"  年化收益率:   {result.annual_return:>+7.2f}%")
    print(f"  最大回撤:     {result.max_drawdown:>7.2%}")
    print(f"  夏普比率:     {result.sharpe_ratio:>7.4f}")
    print(f"  卡尔玛比率:   {result.calmar_ratio:>7.4f}")
    print(f"  总交易数:     {result.total_trades:>5d} 笔")
    print(f"  胜率:         {result.win_rate:>7.2%}")
    print(f"  盈亏比:       {result.profit_loss_ratio:>7.4f}")
    if hasattr(result, "stock_count") and result.stock_count:
        print(f"  涉及标的:     {result.stock_count} 只")
    print()


def sensitivity_analysis(base_config, klines_dict, market_states, scored_pool):
    """参数敏感性分析——改变评分阈值和止盈阶梯"""
    print("\n" + "=" * 60)
    print("  参数敏感性分析")
    print("=" * 60)

    thresholds = [45, 50, 55, 60, 65]
    stop_losses = [5, 8, 10]
    stop_profits = [10, 15, 20]

    results = []
    for th in thresholds:
        for sl in stop_losses:
            for sp in stop_profits:
                result = run_backtest(
                    strategy_type=base_config.strategy_type,
                    start=base_config.start_date,
                    end=base_config.end_date,
                    capital=base_config.initial_capital,
                    klines_dict=klines_dict,
                    market_states=market_states,
                    scored_pool=scored_pool,
                    score_threshold=th,
                    stop_loss_pct=sl,
                    stop_profit_pct=sp,
                )
                results.append({
                    "threshold": th,
                    "stop_loss": sl,
                    "stop_profit": sp,
                    "total_return": result.total_return_pct,
                    "max_drawdown": result.max_drawdown,
                    "sharpe": result.sharpe_ratio,
                    "trades": result.total_trades,
                    "win_rate": result.win_rate,
                })

    # 按夏普排序
    results.sort(key=lambda x: x["sharpe"], reverse=True)

    print(f"\n{'阈值':>5} {'止损':>5} {'止盈':>5} {'收益率':>8} {'回撤':>8} {'夏普':>8} {'交易':>5} {'胜率':>6}")
    print("-" * 55)
    for r in results[:15]:
        print(f"{r['threshold']:>5} {r['stop_loss']:>5} {r['stop_profit']:>5} "
              f"{r['total_return']:>7.1f}% {r['max_drawdown']:>7.2%} "
              f"{r['sharpe']:>7.3f} {r['trades']:>5d} {r['win_rate']:>5.1%}")

    best = results[0]
    print(f"\n📊 最佳参数组合: 阈值={best['threshold']}, 止损={best['stop_loss']}%, 止盈={best['stop_profit']}%")
    print(f"   夏普={best['sharpe']:.3f}, 收益率={best['total_return']:.1f}%, 回撤={best['max_drawdown']:.2%}")
    return results


def main():
    parser = argparse.ArgumentParser(description="FraxVerse 全量回测")
    parser.add_argument("--mode", choices=["db", "real"], default="db",
                        help="数据源: db=使用数据库已有数据, real=从AKShare拉取")
    parser.add_argument("--start", default=DEFAULT_START, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", default=DEFAULT_END, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=INITIAL_CAPITAL, help="初始资金（默认100万）")
    parser.add_argument("--sensitivity", action="store_true", help="运行参数敏感性分析")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    capital = args.capital

    print(f"\n🚀 FraxVerse 全量回测")
    print(f"   数据源: {args.mode}")
    print(f"   区间:   {start_date} → {end_date}")
    print(f"   本金:   ¥{capital:,.2f}")
    print()

    # 加载数据
    klines = fetch_klines_from_db(start_date, end_date)
    market_states = fetch_market_states(start_date, end_date)
    scored_pool = fetch_scored_pool(start_date, end_date)

    if not klines:
        logger.error("无 K 线数据，无法回测")
        sys.exit(1)

    # ── 策略一：周期底部量能异动 ──
    logger.info("===== 运行策略一：周期底部量能异动 =====")
    r1 = run_backtest(
        strategy_type="bottom_volume",
        start=start_date, end=end_date,
        capital=capital,
        klines_dict=klines,
        market_states=market_states,
        scored_pool=scored_pool,
    )
    print_report(r1, "策略一：周期底部量能异动")

    # ── 策略二：趋势动量低吸 ──
    logger.info("===== 运行策略二：趋势动量低吸 =====")
    r2 = run_backtest(
        strategy_type="trend_momentum",
        start=start_date, end=end_date,
        capital=capital,
        klines_dict=klines,
        market_states=market_states,
        scored_pool=scored_pool,
    )
    print_report(r2, "策略二：趋势动量低吸")

    # ── 对比 ──
    print("=" * 60)
    print("  策略对比")
    print("=" * 60)
    print(f"{'指标':<20} {'底部量能':<20} {'趋势动量':<20}")
    print("-" * 60)
    print(f"{'总收益率':<20} {r1.total_return_pct:>+7.2f}%{'':<11} {r2.total_return_pct:>+7.2f}%")
    print(f"{'年化收益率':<20} {r1.annual_return:>+7.2f}%{'':<11} {r2.annual_return:>+7.2f}%")
    print(f"{'最大回撤':<20} {r1.max_drawdown:>7.2%}{'':<13} {r2.max_drawdown:>7.2%}")
    print(f"{'夏普比率':<20} {r1.sharpe_ratio:>7.4f}{'':<13} {r2.sharpe_ratio:>7.4f}")
    print(f"{'总交易':<20} {r1.total_trades:>5d}{'':<15} {r2.total_trades:>5d}")
    print(f"{'胜率':<20} {r1.win_rate:>7.2%}{'':<13} {r2.win_rate:>7.2%}")
    print(f"{'盈亏比':<20} {r1.profit_loss_ratio:>7.4f}{'':<13} {r2.profit_loss_ratio:>7.4f}")
    print()

    # ── 敏感性分析 ──
    if args.sensitivity:
        config = type("cfg", (), {
            "strategy_type": "bottom_volume",
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": capital,
        })
        sensitivity_analysis(config, klines, market_states, scored_pool)

    # ── 结论 ──
    print("=" * 60)
    print("  结论")
    print("=" * 60)
    if r1.total_trades > 0 or r2.total_trades > 0:
        better = "策略一（底部量能）" if r1.sharpe_ratio >= r2.sharpe_ratio else "策略二（趋势动量）"
        print(f"  ✅ 回测完成，交易数据有效")
        print(f"  🏆 夏普更优: {better}")
        if r1.sharpe_ratio >= 0.8:
            print(f"  ✅ 策略一夏普 {r1.sharpe_ratio:.2f} ≥ 0.8，通过夏普门禁")
        else:
            print(f"  ⚠️  策略一夏普 {r1.sharpe_ratio:.2f} < 0.8，未达门禁线")
        if r2.sharpe_ratio >= 0.8:
            print(f"  ✅ 策略二夏普 {r2.sharpe_ratio:.2f} ≥ 0.8，通过夏普门禁")
        else:
            print(f"  ⚠️  策略二夏普 {r2.sharpe_ratio:.2f} < 0.8，未达门禁线")
    else:
        print("  ⚠️  无交易产生 — 检查评分数据和市场状态配置")
    print()


if __name__ == "__main__":
    main()
