"""
FraxVerse 回测调度器 — 将策略流程（粗筛→评分→选股→交易信号）集成到回测引擎

设计思想（对齐 DD-03 §4.4）：
- BacktestRunner 作为桥梁，连接策略引擎（screener/scorer）和回测引擎（BacktestingEngine）
- 对回测区间内每个交易日：粗筛 → 评分 → 选Top15 → 生成TradeSignal
- 按信号驱动 BacktestingEngine 对每只标的逐标回测
- PortfolioResult 聚合为组合绩效

P0-6.2: 策略一「周期底部量能异动」回测
P0-6.3: 策略二「趋势动量低吸」回测
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from src.engine.backtesting import (
    BacktestingEngine,
    BacktestResult,
    PortfolioBacktester,
    PortfolioResult,
    TradeSignal,
)

logger = logging.getLogger(__name__)

# ── 策略一回测参数 ────────────────────────────────────────────────
STRATEGY1_SCORE_THRESHOLD = 55.0  # 评分≥55才入场
STRATEGY1_STOP_LOSS_PCT = 8.0     # 止损-8%
STRATEGY1_STOP_PROFIT_PCT = 15.0  # 止盈+15%
STRATEGY1_POSITION_PCT = 20.0     # 单票仓位20%
STRATEGY1_ALLOWED_STATES = {"底部机会期"}

# ── 策略二回测参数 ────────────────────────────────────────────────
STRATEGY2_SCORE_THRESHOLD = 55.0
STRATEGY2_STOP_LOSS_PCT = 8.0
STRATEGY2_STOP_PROFIT_PCT = 15.0
STRATEGY2_POSITION_PCT = 25.0
STRATEGY2_ALLOWED_STATES = {"主线确认", "趋势上升期"}

# ── 公共参数 ──────────────────────────────────────────────────────
DEFAULT_CAPITAL = 1_000_000.0


@dataclass
class BacktestConfig:
    """回测配置"""
    strategy_type: str = "bottom_volume"
    start_date: date | None = None
    end_date: date | None = None
    initial_capital: float = DEFAULT_CAPITAL
    score_threshold: float = STRATEGY1_SCORE_THRESHOLD
    stop_loss_pct: float = STRATEGY1_STOP_LOSS_PCT
    stop_profit_pct: float = STRATEGY1_STOP_PROFIT_PCT
    position_pct: float = STRATEGY1_POSITION_PCT
    allowed_states: set[str] = field(default_factory=lambda: STRATEGY1_ALLOWED_STATES)
    params: dict = field(default_factory=dict)


def get_config_for_strategy(strategy_type: str) -> BacktestConfig:
    """根据策略类型获取默认回测配置"""
    if strategy_type == "trend_momentum":
        return BacktestConfig(
            strategy_type="trend_momentum",
            score_threshold=STRATEGY2_SCORE_THRESHOLD,
            stop_loss_pct=STRATEGY2_STOP_LOSS_PCT,
            stop_profit_pct=STRATEGY2_STOP_PROFIT_PCT,
            position_pct=STRATEGY2_POSITION_PCT,
            allowed_states=STRATEGY2_ALLOWED_STATES,
        )
    return BacktestConfig(strategy_type="bottom_volume")


def run_backtest(
    strategy_type: str = "bottom_volume",
    start: str | date | None = None,
    end: str | date | None = None,
    capital: float = DEFAULT_CAPITAL,
    klines_dict: dict[str, pd.DataFrame] | None = None,
    market_states: dict[str, str] | None = None,
    scored_pool: dict[str, list[dict]] | None = None,
    **kwargs,
) -> PortfolioResult:
    """运行策略回测

    这是 P0-6.2/P0-6.3 的主入口函数。

    Args:
        strategy_type: "bottom_volume" 或 "trend_momentum"
        start: 回测开始日期
        end: 回测结束日期
        capital: 初始资金
        klines_dict: {stock_code: DataFrame} 所有候选标的K线
        market_states: {date_str: state_name} 每日市场状态
        scored_pool: {date_str: [{stock_code, score, ...}]} 每日评分结果
        **kwargs: 其他回测参数

    Returns:
        PortfolioResult 组合回测结果
    """
    config = get_config_for_strategy(strategy_type)
    if kwargs:
        config = _merge_config(config, kwargs)

    # 处理日期格式
    start_date = _parse_date(start) if start else date(2024, 1, 1)
    end_date = _parse_date(end) if end else date(2024, 12, 31)
    config.start_date = start_date
    config.end_date = end_date
    config.initial_capital = capital

    if not klines_dict:
        logger.warning("run_backtest: 未提供K线数据，返回空结果")
        return PortfolioResult(
            strategy_type=strategy_type,
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            final_capital=capital,
        )

    # 生成交易信号
    signals_dict = _generate_signals(
        market_states or {}, scored_pool or {}, config
    )

    if not signals_dict:
        logger.info("run_backtest: 未生成任何交易信号")
        return PortfolioResult(
            strategy_type=strategy_type,
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            final_capital=capital,
        )

    # 逐标回测
    engine_results: dict[str, BacktestResult] = {}
    for stock_code, klines in klines_dict.items():
        signals = signals_dict.get(stock_code, [])
        if not signals:
            continue

        bt = BacktestingEngine()
        bt.set_parameters(
            data=klines,
            start=start_date,
            end=end_date,
            capital=capital / max(len(signals_dict), 1),
            signals=signals,
        )
        result = bt.run()
        result.strategy_type = strategy_type
        engine_results[stock_code] = result

    # 聚合
    pb = PortfolioBacktester(
        strategy_type=strategy_type,
        start_date=start_date,
        end_date=end_date,
        initial_capital=capital,
    )
    return pb._aggregate(engine_results)


def _generate_signals(
    market_states: dict[str, str],
    scored_pool: dict[str, list[dict]],
    config: BacktestConfig,
) -> dict[str, list[TradeSignal]]:
    """根据市场状态和评分结果生成交易信号

    按日遍历回测区间，对每只标的检查是否符合入场条件。
    入场条件：
      - 当日市场状态在 allowed_states 中
      - 当日该标的评分 >= score_threshold
      - 该标的当日通过粗筛（在scored_pool中）
    出场条件：
      - 标的不再出现在评分池中（评分下降）
      - 止损/止盈由 BacktestingEngine 的 stop_loss/stop_profit 处理
    """
    if not market_states or not scored_pool:
        logger.info("_generate_signals: 缺少市场状态或评分数据，无法生成信号")
        return {}

    # 按日期排序
    sorted_dates = sorted(scored_pool.keys())
    if not sorted_dates:
        return {}

    # 收集所有出现过的标的
    all_stocks = set()
    daily_candidates: dict[str, dict[str, float]] = {}
    for d in sorted_dates:
        candidates = scored_pool.get(d, [])
        stock_scores = {}
        for c in candidates:
            code = c.get("stock_code", "")
            score = c.get("score_total", 0)
            if code:
                stock_scores[code] = score
                all_stocks.add(code)
        daily_candidates[d] = stock_scores

    signals_dict: dict[str, list[TradeSignal]] = {s: [] for s in all_stocks}
    holdings: dict[str, bool] = {}  # 当前是否持仓

    for d in sorted_dates:
        state = market_states.get(d, "非主线状态")
        stock_scores = daily_candidates.get(d, {})

        for stock_code in all_stocks:
            score = stock_scores.get(stock_code, 0.0)
            is_in_pool = stock_code in stock_scores
            is_allowed_state = state in config.allowed_states
            is_qualified = is_in_pool and is_allowed_state and score >= config.score_threshold

            if is_qualified and not holdings.get(stock_code):
                # 买入信号
                signals_dict[stock_code].append(TradeSignal(
                    date=_parse_date(d),
                    action="buy",
                    position_pct=config.position_pct,
                    stop_loss=config.stop_loss_pct,
                    stop_profit=config.stop_profit_pct,
                    reason=f"{config.strategy_type}: 评分{score:.1f} 状态{state}",
                ))
                holdings[stock_code] = True

            elif not is_qualified and holdings.get(stock_code):
                # 卖出信号（评分下降、状态改变、或不在池中）
                signals_dict[stock_code].append(TradeSignal(
                    date=_parse_date(d),
                    action="sell",
                    reason=f"出场: 评分{score:.1f} 状态{state}",
                ))
                holdings[stock_code] = False
    return signals_dict


def _merge_config(base: BacktestConfig, overrides: dict) -> BacktestConfig:
    """合并配置覆盖"""
    for k, v in overrides.items():
        if hasattr(base, k):
            setattr(base, k, v)
    return base


def _parse_date(d: str | date) -> date:
    """统一日期解析"""
    if isinstance(d, date):
        return d
    return pd.Timestamp(d).date()
