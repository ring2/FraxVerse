"""五维度评分模块

P0-4.1: 对粗筛候选标的进行五维度评分、排序、选取最佳开仓标的

五维度（权重）:
1. 趋势强度 TrendStrength   (0.30) — ADX + 均线斜率 + 价格相对位置
2. 资金热度 CapitalHeat       (0.25) — 板块集中度 + 日均成交额
3. 回调/底部深度 PullbackDepth (0.20) — 策略一分跌幅+量缩止跌, 策略二看缩量比+跌幅衰减
4. 流动性安全 LiquiditySafety  (0.15) — 成交额 + 市值 + 换手率
5. 形态健康度 PatternHealth    (0.10) — 均线排列 + 成交量异常 + 上影线
"""

import logging
from dataclasses import dataclass, field

from src.strategy.screener import StrategyCandidate

logger = logging.getLogger(__name__)

# ── 评分权重 ──────────────────────────────────────────────────────

WEIGHTS: dict[str, float] = {
    "trend_strength": 0.30,
    "capital_heat": 0.25,
    "pullback_depth": 0.20,
    "liquidity_safety": 0.15,
    "pattern_health": 0.10,
}


# ── 数据类 ────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    """单维度评分"""
    name: str
    score: float      # 0-100
    weight: float     # 固定权重
    detail: str = ""

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class ScoredCandidate:
    """评分后的候选标的"""
    stock_code: str
    stock_name: str
    total_score: float = 0.0
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    signal: str = ""           # buy / buy_low / buy_high / cancel_reserve / exit
    strategy: str = ""         # strategy1 / strategy2
    reason: str = ""
    daily_amount: float = 0.0


# ── 维度一：趋势强度 ──────────────────────────────────────────────

def score_trend_strength(candidate: StrategyCandidate) -> DimensionScore:
    """基于 ADX + 价格相对均线位置 + 均线斜率"""
    detail = candidate.detail
    adx = detail.get("adx", 0.0)
    mas = detail.get("mas", {})
    last_close = detail.get("last_close")
    ma_slope = detail.get("ma_slope", 0.0)

    # ADX 基础分
    if adx >= 40:
        base = 100.0
    elif adx >= 30:
        base = 80.0
    elif adx >= 25:
        base = 60.0
    elif adx >= 20:
        base = 40.0
    else:
        base = 20.0

    # 价格相对 MA5 位置加成
    ma5 = mas.get("ma5") if mas else None
    penalty = 0.0
    bonus = 0.0
    if last_close is not None and ma5 is not None and ma5 > 0:
        if last_close > ma5:
            bonus += 10.0
        elif last_close < ma5:
            penalty += 10.0

    # 均线斜率加成
    if ma_slope > 0:
        bonus += 10.0

    score = min(100.0, max(0.0, base - penalty + bonus))
    return DimensionScore(
        name="trend_strength",
        score=score,
        weight=WEIGHTS["trend_strength"],
        detail=f"ADX={adx:.1f}, base={base:.0f}, bonus={bonus:.0f}, penalty={penalty:.0f}",
    )


# ── 维度二：资金热度 ──────────────────────────────────────────────

def score_capital_heat(candidate: StrategyCandidate) -> DimensionScore:
    """基于板块资金集中度 + 个股日均成交额"""
    detail = candidate.detail
    sector_ratio = detail.get("sector_ratio")
    avg_amount = detail.get("avg_amount", 0.0)

    # 板块集中度分
    sector_score = 20.0
    if sector_ratio is not None:
        if sector_ratio >= 0.6:
            sector_score = 100.0
        elif sector_ratio >= 0.4:
            sector_score = 80.0
        elif sector_ratio >= 0.3:
            sector_score = 60.0
        elif sector_ratio >= 0.2:
            sector_score = 40.0

    # 日均成交额分（亿）
    amt_yi = avg_amount / 100_000_000  # 转亿
    amount_score = 20.0
    if amt_yi >= 10:
        amount_score = 100.0
    elif amt_yi >= 5:
        amount_score = 80.0
    elif amt_yi >= 1:
        amount_score = 60.0
    elif amt_yi >= 0.5:
        amount_score = 40.0

    score = (sector_score + amount_score) / 2 if sector_ratio is not None else amount_score

    return DimensionScore(
        name="capital_heat",
        score=score,
        weight=WEIGHTS["capital_heat"],
        detail=f"sector={sector_score:.0f}, amount={amount_score:.0f}",
    )


# ── 维度三：回调/底部深度 ─────────────────────────────────────────

def score_pullback_depth(candidate: StrategyCandidate) -> DimensionScore:
    """策略一：近60日跌幅 + 量缩止跌；策略二：缩量回调比 + 跌幅衰减"""
    detail = candidate.detail
    strategy = detail.get("strategy", "strategy2")
    max_drawdown_60d = detail.get("max_drawdown_60d", 0.0)
    volume_ratio = detail.get("volume_ratio", 1.0)
    pct_changes = detail.get("pct_changes", [])

    if strategy == "strategy1":
        # 跌幅基础：≥30%才开始计分
        if max_drawdown_60d <= -30:
            drop_score = 80.0 + (abs(max_drawdown_60d) - 30) // 10 * 5
        else:
            drop_score = 0.0

        # 量缩止跌加分
        if volume_ratio < 0.6:
            drop_score += 20.0

        score = min(100.0, drop_score)

    else:
        # 缩量比分
        if volume_ratio <= 0.5:
            base = 100.0
        elif volume_ratio <= 0.7:
            base = 80.0
        elif volume_ratio <= 0.85:
            base = 60.0
        elif volume_ratio <= 1.0:
            base = 40.0
        else:
            base = 20.0

        # 跌幅衰减：近3日涨幅过大 → 缩量分的信赖度降低
        if pct_changes:
            avg_pct = sum(pct_changes) / len(pct_changes)
            decay = 1.0 - min(abs(avg_pct) / 20.0, 0.8)
            base *= max(decay, 0.2)

        score = base

    return DimensionScore(
        name="pullback_depth",
        score=score,
        weight=WEIGHTS["pullback_depth"],
        detail=f"strategy={strategy}, vol_ratio={volume_ratio:.2f}, drawdown={max_drawdown_60d:.1f}",  # noqa: E501
    )


# ── 维度四：流动性安全 ────────────────────────────────────────────

def score_liquidity_safety(candidate: StrategyCandidate) -> DimensionScore:
    """日成交额 + 市值 + 换手率"""
    detail = candidate.detail
    avg_amount = detail.get("avg_amount", 0.0)
    market_cap = detail.get("market_cap", 0.0)
    turnover_rate = detail.get("turnover_rate", 0.0)

    # 成交额分（40分）
    amt_yi = avg_amount / 100_000_000
    if amt_yi >= 10:
        amt_score = 40.0
    elif amt_yi >= 5:
        amt_score = 30.0
    elif amt_yi >= 1:
        amt_score = 20.0
    elif amt_yi >= 0.5:
        amt_score = 10.0
    else:
        amt_score = 0.0

    # 市值分（40分）
    cap_yi = market_cap / 100_000_000
    if 50 <= cap_yi <= 500:
        cap_score = 40.0
    elif (20 <= cap_yi < 50) or (500 < cap_yi <= 1000):
        cap_score = 30.0
    else:
        cap_score = 10.0

    # 换手率分（20分）
    turnover_pct = turnover_rate * 100  # 转百分比
    if 3 <= turnover_pct <= 10:
        turnover_score = 20.0
    elif 1 <= turnover_pct < 3:
        turnover_score = 10.0
    else:
        turnover_score = 0.0

    score = amt_score + cap_score + turnover_score
    return DimensionScore(
        name="liquidity_safety",
        score=min(100.0, score),
        weight=WEIGHTS["liquidity_safety"],
        detail=f"amt={amt_score:.0f}, cap={cap_score:.0f}, turnover={turnover_score:.0f}",
    )


# ── 维度五：形态健康度 ────────────────────────────────────────────

def score_pattern_health(candidate: StrategyCandidate) -> DimensionScore:
    """均线排列 + 成交量异常 + 上影线"""
    detail = candidate.detail
    mas = detail.get("mas", {})
    recent_volume_ratio = detail.get("recent_volume_ratio", 1.0)
    upper_shadow_ratio = detail.get("upper_shadow_ratio", 0.0)
    pct_changes = detail.get("pct_changes", [])

    # 均线排列（50分）
    if mas and all(k in mas for k in ("ma5", "ma10", "ma20", "ma60")):
        if mas["ma5"] >= mas["ma10"] >= mas["ma20"] >= mas["ma60"]:
            arrange_score = 50.0
        elif mas["ma5"] >= mas["ma10"] >= mas["ma20"]:
            arrange_score = 30.0
        else:
            arrange_score = 10.0
    else:
        arrange_score = 10.0

    # 成交量异常（30分）
    if recent_volume_ratio >= 2.0:
        # 判断阴阳线
        if pct_changes and sum(pct_changes) / len(pct_changes) < 0:
            vol_score = -20.0  # 放量阴线 → 扣分
        else:
            vol_score = 10.0   # 放量阳线 → 加分
    else:
        vol_score = 30.0       # 量正常

    # 上影线（20分）
    shadow_score = -10.0 if upper_shadow_ratio >= 3.0 else 20.0

    score = arrange_score + vol_score + shadow_score
    return DimensionScore(
        name="pattern_health",
        score=max(0.0, min(100.0, score)),
        weight=WEIGHTS["pattern_health"],
        detail=f"arrange={arrange_score:.0f}, vol={vol_score:.0f}, shadow={shadow_score:.0f}",
    )


# ── 评分函数映射 ──────────────────────────────────────────────────

_DIMENSION_SCORERS = {
    "trend_strength": score_trend_strength,
    "capital_heat": score_capital_heat,
    "pullback_depth": score_pullback_depth,
    "liquidity_safety": score_liquidity_safety,
    "pattern_health": score_pattern_health,
}


# ── 主评分入口 ────────────────────────────────────────────────────

def score_candidates(candidates: list[StrategyCandidate]) -> list[ScoredCandidate]:
    """对候选列表进行五维度评分，返回按总分降序排列的结果"""
    if not candidates:
        return []

    results: list[ScoredCandidate] = []

    for c in candidates:
        dimensions: dict[str, DimensionScore] = {}
        for dim_name, scorer_fn in _DIMENSION_SCORERS.items():
            try:
                ds = scorer_fn(c)
            except Exception as e:
                logger.warning("评分维度 %s 计算失败: %s", dim_name, e)
                ds = DimensionScore(  # noqa: E501
                    name=dim_name, score=0.0, weight=WEIGHTS[dim_name], detail=str(e),
                )
            dimensions[dim_name] = ds

        total = sum(ds.weighted for ds in dimensions.values())

        signal = _determine_signal(total, c)
        strategy = c.detail.get("strategy", "")

        results.append(ScoredCandidate(
            stock_code=c.stock_code,
            stock_name=c.stock_name,
            total_score=round(total, 2),
            dimensions=dimensions,
            signal=signal,
            strategy=strategy,
            reason=c.reason,
            daily_amount=c.daily_amount,
        ))

    results.sort(key=lambda r: r.total_score, reverse=True)
    return results


def _determine_signal(total_score: float, candidate: StrategyCandidate) -> str:  # noqa: ARG001
    """根据总分和候选特征确定信号"""
    if total_score >= 85:
        return "buy"
    elif total_score >= 70:
        return "buy_low"
    elif total_score >= 50:
        return "buy_high"
    return "cancel_reserve"


# ── 最佳选取 ──────────────────────────────────────────────────────

def choose_best(
    strategy1_candidates: list[ScoredCandidate],
    strategy2_candidates: list[ScoredCandidate],
    max_picks: int = 3,
) -> list[ScoredCandidate]:
    """从两个策略的评分结果中选取最终开仓标的（1-3只）

    规则：
    1. 每个策略取 top N
    2. 合并去重（同一股票出现在两个策略中，保留策略二的评分）
    3. 同策略同评分选成交额大的
    4. 最终不超过 max_picks 只
    """
    if not strategy1_candidates and not strategy2_candidates:
        return []

    # 每个策略取 top 5（留足合并空间）
    top1 = sorted(strategy1_candidates, key=lambda r: r.total_score, reverse=True)[:5]
    top2 = sorted(strategy2_candidates, key=lambda r: r.total_score, reverse=True)[:5]

    # 合并去重，策略二优先
    seen: set[str] = set()
    merged: list[ScoredCandidate] = []

    # 策略二的候选优先加入
    for r in top2:
        if r.stock_code not in seen:
            seen.add(r.stock_code)
            merged.append(r)

    # 策略一的候选补充（未被策略二覆盖的）
    for r in top1:
        if r.stock_code not in seen:
            seen.add(r.stock_code)
            merged.append(r)

    # 按总分降序
    merged.sort(key=lambda r: r.total_score, reverse=True)

    # 取 top N
    picks = merged[:max_picks]

    # 同分情况按成交额排序
    final: list[ScoredCandidate] = []
    current_score = None
    batch: list[ScoredCandidate] = []
    for r in picks:
        if current_score is None or abs(r.total_score - current_score) > 0.01:
            if batch:
                batch.sort(key=lambda x: x.daily_amount, reverse=True)
                final.extend(batch)
            batch = [r]
            current_score = r.total_score
        else:
            batch.append(r)
    if batch:
        batch.sort(key=lambda x: x.daily_amount, reverse=True)
        final.extend(batch)

    return final[:max_picks]
