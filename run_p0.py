#!/usr/bin/env python3
"""
FraxVerse (碎片宇宙) — P0 联调入口

运行完整策略流程：粗筛 → 评分 → 市场状态 → 回测

用法：
    python run_p0.py                        # 使用默认模拟数据
    python run_p0.py --start 2024-01-01 --end 2024-12-31
    python run_p0.py --mode mock            # 模拟数据模式（默认）
    python run_p0.py --mode real            # 真实数据模式（需数据库）
    python run_p0.py --mock-stocks 10       # 模拟股票数量

输出：
    ├── 粗筛结果：策略一 N只 | 策略二 N只
    ├── 评分排序：前N只股票池（含各维度分）
    ├── 市场状态：XXX
    ├── 回测报告：策略一 胜率XX% | 策略二 胜率XX%
    └── 总执行时间：XX秒
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.engine.backtesting import PortfolioResult
from src.strategy.backtest_runner import run_backtest

logger = logging.getLogger(__name__)

# ── 输出格式常量 ──────────────────────────────────────────────────
SEPARATOR = "━" * 60
SUB_SEPARATOR = "─" * 40


# ═══════════════════════════════════════════════════════════════════
# 模拟数据生成器
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MockData:
    """模拟数据集"""
    klines_dict: dict[str, pd.DataFrame] = field(default_factory=dict)
    market_states: dict[str, str] = field(default_factory=dict)
    scored_pool_s1: dict[str, list[dict]] = field(default_factory=dict)  # 策略一
    scored_pool_s2: dict[str, list[dict]] = field(default_factory=dict)  # 策略二
    stock_names: dict[str, str] = field(default_factory=dict)


def _random_stock_code(n: int) -> str:
    """生成随机股票代码"""
    return f"{np.random.randint(600000, 609999)}.SH" if np.random.random() > 0.5 else f"{np.random.randint(0, 3999):04d}.SZ"


def _make_mock_klines(
    days: int = 260,
    start_price: float = 100.0,
    trend: str = "random",
    seed: int = 0,
) -> pd.DataFrame:
    """生成单只股票的模拟K线"""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start="2024-01-01", periods=days)

    if trend == "up":
        prices = start_price * (1 + np.cumsum(rng.randn(days) * 0.02))
    elif trend == "down":
        prices = start_price * (1 - np.cumsum(rng.randn(days) * 0.02))
    elif trend == "bottom":
        # 先跌60%再横盘
        prices = start_price * (1 - np.cumsum(np.abs(rng.randn(days) * 0.015)))
        prices = np.maximum(prices, start_price * 0.3)
    else:
        prices = start_price * (1 + np.cumsum(rng.randn(days) * 0.025))

    prices = np.maximum(prices, start_price * 0.2)
    # 确保有涨跌
    prices[1:] = prices[1:] + rng.randn(days - 1) * 0.5
    prices = np.maximum(prices, 1.0)

    df = pd.DataFrame({
        "date": dates,
        "Open": prices * (1 - rng.rand(days) * 0.015),
        "High": prices * (1 + rng.rand(days) * 0.025),
        "Low": prices * (1 - rng.rand(days) * 0.025),
        "Close": prices,
        "Volume": rng.randint(1_000_000, 50_000_000, days),
        "amount": rng.randint(100_000_000, 5_000_000_000, days),
        "pct_change": rng.randn(days) * 2.0,
    })
    df.loc[df["pct_change"].abs() < 0.1, "pct_change"] = rng.randn(len(df[df["pct_change"].abs() < 0.1])) * 3.0
    return df


def generate_mock_data(
    start: date,
    end: date,
    num_stocks: int = 10,
) -> MockData:
    """生成完整的模拟数据集"""
    np.random.seed(42)

    mock = MockData()
    stock_codes = []
    stock_names_map = {}

    # 生成股票
    for i in range(num_stocks):
        code = _random_stock_code(i)
        stock_codes.append(code)
        stock_names_map[code] = f"模拟股票{i + 1}"

    # 生成K线
    for i, code in enumerate(stock_codes):
        trend_choice = ["random", "up", "down", "bottom"][i % 4]
        mock.klines_dict[code] = _make_mock_klines(seed=i, trend=trend_choice)

    mock.stock_names = stock_names_map

    # 生成市场状态
    trade_dates = pd.bdate_range(start=start, end=end)
    states = ["非主线状态", "非主线状态", "非主线状态", "底部机会期", "非主线状态",
              "主线确认", "趋势上升期", "趋势上升期", "非主线状态", "非主线状态",
              "底部机会期", "底部机会期", "非主线状态"]
    for i, d in enumerate(trade_dates):
        mock.market_states[d.date().isoformat()] = states[i % len(states)]

    # 生成评分结果
    for i, d in enumerate(trade_dates):
        ds = d.date().isoformat()
        state = mock.market_states[ds]

        if state in ("底部机会期",):
            # 策略一适用的候选
            s1_candidates = []
            for code in stock_codes[:max(1, len(stock_codes) // 2)]:
                base_score = 50 + np.random.randint(-15, 25)
                s1_candidates.append({
                    "stock_code": code,
                    "score_total": float(base_score),
                    "stock_name": stock_names_map[code],
                })
            s1_candidates.sort(key=lambda x: x["score_total"], reverse=True)
            mock.scored_pool_s1[ds] = s1_candidates[:15]

        if state in ("主线确认", "趋势上升期"):
            # 策略二适用的候选
            s2_candidates = []
            for code in stock_codes[max(1, len(stock_codes) // 2):]:
                base_score = 50 + np.random.randint(-10, 30)
                s2_candidates.append({
                    "stock_code": code,
                    "score_total": float(base_score),
                    "stock_name": stock_names_map[code],
                })
            s2_candidates.sort(key=lambda x: x["score_total"], reverse=True)
            mock.scored_pool_s2[ds] = s2_candidates[:15]

        if not mock.scored_pool_s1:
            mock.scored_pool_s1[ds] = []
        if not mock.scored_pool_s2:
            mock.scored_pool_s2[ds] = []

    return mock


# ═══════════════════════════════════════════════════════════════════
# 输出格式化
# ═══════════════════════════════════════════════════════════════════

def _fmt_pct(v: float) -> str:
    """格式化百分比"""
    if v >= 0:
        return f"+{v:.2f}%"
    return f"{v:.2f}%"


def _fmt_trades(n: int) -> str:
    return f"{n}笔交易"


def print_report(
    result_s1: PortfolioResult | None,
    result_s2: PortfolioResult | None,
    mock: MockData | None,
    elapsed: float,
    mode: str,
) -> None:
    """打印格式化报告"""
    print()
    print(SEPARATOR)
    print("  🌌 碎片宇宙 · FraxVerse · P0 全流程验证")
    print(SEPARATOR)

    # 模式
    print(f"  模式: {'📊 模拟数据' if mode == 'mock' else '🔴 真实数据'}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if mock:
        # 粗筛结果
        print("  📋 粗筛结果")
        print(SUB_SEPARATOR)
        s1_count = len(mock.scored_pool_s1.get(next(iter(mock.market_states)), [])) if mock.scored_pool_s1 else 0
        s2_count = len(mock.scored_pool_s2.get(next(iter(mock.market_states)), [])) if mock.scored_pool_s2 else 0
        print(f"    ├── 策略一「周期底部量能异动」: {s1_count} 只")
        print(f"    └── 策略二「趋势动量低吸」:  {s2_count} 只")
        print()

        # 评分排序（取第一个交易日）
        print("  📊 评分排序（前10只）")
        print(SUB_SEPARATOR)
        first_date = sorted(mock.market_states.keys())[0]
        all_pool = []
        for c in mock.scored_pool_s1.get(first_date, []):
            all_pool.append(c)
        for c in mock.scored_pool_s2.get(first_date, []):
            if c["stock_code"] not in {x["stock_code"] for x in all_pool}:
                all_pool.append(c)
        all_pool.sort(key=lambda x: x["score_total"], reverse=True)

        for i, c in enumerate(all_pool[:10]):
            stock_name = mock.stock_names.get(c["stock_code"], c["stock_code"])
            print(f"    {i + 1:>2}. {stock_name} ({c['stock_code']})  "
                  f"总分: {c['score_total']:.1f}")
        if len(all_pool) > 10:
            print(f"    ... 共{len(all_pool)}只")
        print()

        # 市场状态
        print("  🎯 市场状态（最近10个交易日）")
        print(SUB_SEPARATOR)
        sorted_dates = sorted(mock.market_states.keys())
        for d in sorted_dates[-10:]:
            state = mock.market_states[d]
            icon = {"底部机会期": "🔻", "主线确认": "🌟", "趋势上升期": "📈",
                     "非主线状态": "⚪", "观望态": "⚠️"}.get(state, "❓")
            print(f"    {icon} {d}: {state}")

    print()

    # 回测报告
    print("  📈 回测报告")
    print(SUB_SEPARATOR)

    if result_s1:
        _print_strategy_result("策略一", result_s1)
    if result_s2:
        _print_strategy_result("策略二", result_s2)
    if not result_s1 and not result_s2:
        print("    (无回测结果)")

    print()
    print(SEPARATOR)
    print(f"  ⏱  总执行时间: {elapsed:.2f} 秒")
    print(SEPARATOR)
    print()


def _print_strategy_result(name: str, result: PortfolioResult) -> None:
    """打印单策略回测结果"""
    if result.total_trades == 0:
        print(f"    {name}: ⏭️ 无交易信号")
        return

    print(f"    {name}:")
    print(f"      ├── 总交易: {result.total_trades} 笔")
    print(f"      ├── 胜率: {result.win_rate * 100:.1f}%")
    print(f"      ├── 累计收益: {_fmt_pct(result.annual_return)}")
    print(f"      ├── 最大回撤: {result.max_drawdown * 100:.1f}%")
    print(f"      ├── 最终资金: ¥{result.final_capital:,.0f}")
    print(f"      └── 覆盖标的: {result.stock_count} 只")
    if result.individual_results:
        # 显示每只标的的交易数
        for code, r in result.individual_results.items():
            if r.total_trades > 0:
                print(f"          ├─ {code}: {r.total_trades}笔 "
                      f"| 胜率{r.win_rate * 100:.0f}% "
                      f"| 收益{_fmt_pct(r.total_return_pct)}")


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

def run_pipeline(
    start: date,
    end: date,
    mode: str = "mock",
    mock_stocks: int = 10,
) -> tuple[PortfolioResult | None, PortfolioResult | None, MockData | None]:
    """运行完整的P0策略流程

    Returns:
        (策略一回测结果, 策略二回测结果, 模拟数据)
    """
    result_s1: PortfolioResult | None = None
    result_s2: PortfolioResult | None = None
    mock: MockData | None = None

    if mode == "mock":
        # 生成模拟数据
        mock = generate_mock_data(start, end, num_stocks=mock_stocks)

        if not mock.klines_dict:
            logger.warning("未能生成模拟K线数据")
            return None, None, mock

        # 策略一回测
        # 策略一适用于底部机会期
        result_s1 = run_backtest(
            strategy_type="bottom_volume",
            start=start,
            end=end,
            capital=1_000_000,
            klines_dict=mock.klines_dict,
            market_states=mock.market_states,
            scored_pool=mock.scored_pool_s1,
        )

        # 策略二回测
        # 策略二适用于主线确认/趋势上升期
        result_s2 = run_backtest(
            strategy_type="trend_momentum",
            start=start,
            end=end,
            capital=1_000_000,
            klines_dict=mock.klines_dict,
            market_states=mock.market_states,
            scored_pool=mock.scored_pool_s2,
        )

    elif mode == "real":
        # 真实数据模式（P1阶段完善）
        logger.info("真实数据模式待实现，使用模拟数据代替")
        mock = generate_mock_data(start, end, num_stocks=mock_stocks)
        result_s1 = run_backtest(
            strategy_type="bottom_volume",
            start=start,
            end=end,
            klines_dict=mock.klines_dict,
            market_states=mock.market_states,
            scored_pool=mock.scored_pool_s1,
        )
        result_s2 = run_backtest(
            strategy_type="trend_momentum",
            start=start,
            end=end,
            klines_dict=mock.klines_dict,
            market_states=mock.market_states,
            scored_pool=mock.scored_pool_s2,
        )

    return result_s1, result_s2, mock


def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="碎片宇宙 · FraxVerse · P0 全流程联调",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_p0.py                          # 默认模拟模式
  python run_p0.py --start 2024-01-01 --end 2024-12-31
  python run_p0.py --mode real              # 真实数据模式
  python run_p0.py --mock-stocks 20         # 模拟20只股票
        """,
    )
    parser.add_argument("--start", default="2024-01-01", help="回测开始日期 (默认: 2024-01-01)")
    parser.add_argument("--end", default="2024-06-30", help="回测结束日期 (默认: 2024-06-30)")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock",
                        help="运行模式: mock(模拟数据) / real(真实数据) (默认: mock)")
    parser.add_argument("--mock-stocks", type=int, default=10,
                        help="模拟数据中的股票数量 (默认: 10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")

    args = parser.parse_args()

    # 日志
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s | %(message)s")

    start_date = pd.Timestamp(args.start).date()
    end_date = pd.Timestamp(args.end).date()

    print(f"\n  🌌 FraxVerse · P0 全流程联调")
    print(f"  区间: {start_date} → {end_date}")
    print(f"  模式: {'📊 模拟数据' if args.mode == 'mock' else '🔴 真实数据'}")
    print()

    t0 = time.time()

    result_s1, result_s2, mock = run_pipeline(
        start=start_date,
        end=end_date,
        mode=args.mode,
        mock_stocks=args.mock_stocks,
    )

    elapsed = time.time() - t0

    # 输出报告
    print_report(result_s1, result_s2, mock, elapsed, args.mode)


if __name__ == "__main__":
    main()
