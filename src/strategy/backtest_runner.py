"""策略回测编排器

对齐 DD-03 §4.3-4.4 设计。
每天：粗筛 → 评分 → Agent → 交易信号 → 回测引擎。

接管 run_full_backtest.py 中的 run_backtest() 调用。
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from src.engine.backtesting import (
    BacktestingEngine,
    BacktestResult,
    TradeSignal,
)

logger = logging.getLogger(__name__)


def run_backtest(
    strategy_type: str,
    start: date,
    end: date,
    capital: float,
    klines_dict: dict[str, pd.DataFrame],
    market_states: dict[str, str] | None = None,
    scored_pool: dict[str, list[dict]] | None = None,
    score_threshold: float = 0.0,
    stop_loss_pct: float = 8.0,
    stop_profit_pct: float = 15.0,
) -> BacktestResult:
    """完整策略回测 — 从评分池筛选目标 → 生成信号 → 运行回测

    简化版（P0）：基于 scored_pool 的评分数据生成买卖信号，
    在每只目标标的上逐日模拟交易。

    Args:
        strategy_type: 策略类型 (bottom_volume / trend_momentum)
        start: 回测起始日期
        end: 回测结束日期
        capital: 初始资金
        klines_dict: {stock_code -> K线DataFrame}
        market_states: 可选，{date_str -> market_state}
        scored_pool: 可选，{date_str -> [{stock_code, score_total, strategy_type}]}
        score_threshold: 评分阈值，低于此值不入选
        stop_loss_pct: 止损百分比
        stop_profit_pct: 止盈百分比

    Returns:
        聚合后的 BacktestResult
    """
    logger.info(
        "开始回测 strategy=%s %s→%s capital=%.0f threshold=%.0f sl=%.1f tp=%.1f",
        strategy_type, start, end, capital,
        score_threshold, stop_loss_pct, stop_profit_pct,
    )

    # 如果没有评分池数据，对所有标的直接跑买入持有策略
    if not scored_pool:
        logger.warning("无评分池数据，回滚为策略标的自定义信号")
        return _run_simple_backtest(strategy_type, start, end, capital, klines_dict)

    # 从评分池生成交易信号
    all_signals: dict[str, list[TradeSignal]] = {}
    scored_stocks: set[str] = set()

    for date_str, picks in sorted(scored_pool.items()):
        d = date.fromisoformat(date_str)
        for pick in picks:
            code = pick["stock_code"]
            score = pick.get("score_total", 0)
            st = pick.get("strategy_type", "")

            # 策略类型过滤 + 评分阈值过滤
            if st and st != strategy_type:
                continue
            if score < score_threshold:
                continue

            scored_stocks.add(code)
            if code not in all_signals:
                all_signals[code] = []

            # 买入信号：评分≥阈值日买入
            all_signals[code].append(TradeSignal(
                date=d,
                action="buy",
                position_pct=20.0,   # 每只仓位20%
                stop_loss=stop_loss_pct,
                stop_profit=stop_profit_pct,
                reason=f"评分{score:.1f}≥{score_threshold}",
            ))

    if not all_signals:
        logger.warning("评分池数据但无标的通过评分阈值 %.0f", score_threshold)
        return _run_simple_backtest(strategy_type, start, end, capital, klines_dict)

    # 对每只标的独立回测，然后聚合
    engine_list: list[BacktestingEngine] = []
    for code in scored_stocks:
        klines = klines_dict.get(code)
        if klines is None or klines.empty:
            continue

        signals = all_signals.get(code, [])
        if not signals:
            continue

        eng = BacktestingEngine()
        eng.set_parameters(
            data=klines,
            start=start,
            end=end,
            capital=capital / max(len(scored_stocks), 1),
            signals=signals,
        )
        result = eng.run()
        result.strategy_type = strategy_type
        engine_list.append(eng)

    logger.info("回测完成: %d 只标的参与", len(engine_list))

    if not engine_list:
        return BacktestResult(
            strategy_type=strategy_type,
            start_date=start,
            end_date=end,
            initial_capital=capital,
            final_capital=capital,
            total_trades=0,
        )

    # 聚合所有子结果
    return _aggregate_results(engine_list, strategy_type, start, end, capital)


def _aggregate_results(
    engines: list[BacktestingEngine],
    strategy_type: str,
    start: date,
    end: date,
    capital: float,
) -> BacktestResult:
    """聚合多个标的的回测结果"""
    total_trades = 0
    total_pnl = 0.0
    winning = 0
    losing = 0
    all_daily_equity: dict[str, float] = {}
    max_dd_val = 0.0

    for eng in engines:
        r = eng.result
        if r is None:
            continue
        total_trades += r.total_trades
        total_pnl += (r.final_capital - r.initial_capital)

        # 合并每日净值
        for d, val in r.daily_equity.items():
            all_daily_equity[d] = all_daily_equity.get(d, 0.0) + val

        # 找胜率和盈亏比
        if hasattr(eng, "_trades"):
            for t in eng._trades:  # noqa: SLF001
                if t.pnl > 0:
                    winning += 1
                else:
                    losing += 1

    final_capital = capital + total_pnl

    # 年化收益率
    annual_return_pct = 0.0
    days = (end - start).days
    total_ret = (final_capital / capital - 1) if capital > 0 else 0
    if days > 0 and total_ret > -1:
        annual_return_pct = ((1 + total_ret) ** (365.0 / days) - 1) * 100

    # 最大回撤
    if all_daily_equity:
        sorted_vals = [all_daily_equity[k] for k in sorted(all_daily_equity.keys())]
        peak = sorted_vals[0]
        for val in sorted_vals:
            peak = max(peak, val)
            if peak > 0:
                dd = (peak - val) / peak
                max_dd_val = max(max_dd_val, dd)

    # 胜率
    win_rate = winning / total_trades if total_trades > 0 else 0.0

    # 夏普比率（简化版）
    sharpe = 0.0
    if all_daily_equity:
        sorted_dates = sorted(all_daily_equity.keys())
        daily_rets = []
        for i in range(1, len(sorted_dates)):
            prev = all_daily_equity[sorted_dates[i - 1]]
            curr = all_daily_equity[sorted_dates[i]]
            if prev > 0:
                daily_rets.append((curr - prev) / prev)
        if len(daily_rets) > 1:
            import numpy as np
            mean_ret = np.mean(daily_rets)
            std_ret = np.std(daily_rets, ddof=1)
            sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0.0

    return BacktestResult(
        strategy_type=strategy_type,
        start_date=start,
        end_date=end,
        initial_capital=capital,
        final_capital=round(final_capital, 2),
        annual_return=round(annual_return_pct, 4),
        max_drawdown=round(max_dd_val, 4),
        win_rate=round(win_rate, 4),
        profit_loss_ratio=0.0,
        total_trades=total_trades,
        total_return_pct=round(total_ret * 100, 2),
        sharpe_ratio=round(sharpe, 4),
        calmar_ratio=round(annual_return_pct / (max_dd_val * 100), 4) if max_dd_val > 0 else 0.0,
        daily_equity=all_daily_equity,
    )


def _run_simple_backtest(
    strategy_type: str,
    start: date,
    end: date,
    capital: float,
    klines_dict: dict[str, pd.DataFrame],
) -> BacktestResult:
    """无评分池时的简化回测：对每只标的用简单买入持有策略"""
    engines: list[BacktestingEngine] = []
    for code, klines in klines_dict.items():
        if klines.empty:
            continue
        eng = BacktestingEngine()
        eng.set_parameters(
            data=klines,
            start=start,
            end=end,
            capital=capital / max(len(klines_dict), 1),
        )
        eng._run_hold_strategy(eng._prepare_data())  # noqa: SLF001
        eng._result = eng._calculate_result()  # noqa: SLF001
        engines.append(eng)

    return _aggregate_results(engines, strategy_type, start, end, capital)
