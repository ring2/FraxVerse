"""
FraxVerse · 加权投票决策

严格按 DD-04-AI-Agent模块.md 第4.9节实现。

核心约束：
- [PRD-T-100] 权重动态分配：主线明确 vs 震荡市
- [PRD-T-101] 极端行情：风控一票否决
- [PRD-T-102] 每个Agent必须输出买入理由+反对理由
- [PRD-T-103] 买入理由总分>反对理由总分+阈值才开仓
"""
from __future__ import annotations

import logging
from typing import Any

from src.agent.models import (
    AgentName,
    AgentOutput,
    DecisionType,
    WeightedVoteResult,
)

logger = logging.getLogger(__name__)

# 默认阈值配置
DEFAULT_DECISION_THRESHOLD = 10.0  # 买入理由 > 反对理由 + 阈值 才开仓 [PRD-T-103]
DEFAULT_MIN_DAILY_VOLUME = 50_000_000  # 5千万（流动性检查）


def weighted_vote(
    stock_code: str,
    market_state: str,
    outputs: list[AgentOutput],
    weights: list[dict[str, Any]],
    convergence_method: str = "normal",
    decision_threshold: float = DEFAULT_DECISION_THRESHOLD,
    min_daily_volume: float = DEFAULT_MIN_DAILY_VOLUME,
    daily_volume: float | None = None,
    risk_events_active: bool = False,
) -> WeightedVoteResult:
    """
    加权投票决策。

    对应 DD-04 第4.9节 weighted_vote 伪代码。

    Args:
        stock_code: 股票代码
        market_state: 当前市场状态
        outputs: 校验后的 Agent 输出列表
        weights: 权重配置列表 [{agent_name, market_state, effective_weight, ...}]
        convergence_method: 收敛方法
        decision_threshold: 决策阈值 [PRD-T-103]
        min_daily_volume: 最低日均成交额（流动性检查）
        daily_volume: 当日成交额（None=跳过流动性检查）
        risk_events_active: 是否存在未解决风控事件

    Returns:
        WeightedVoteResult 加权投票结果
    """
    # ──── 1. 读取权重配置 [PRD-T-100] ────
    weight_map: dict[str, float] = {}
    for w in weights:
        if w.get("market_state") == market_state:
            weight_map[w["agent_name"]] = float(w.get("effective_weight", 0.25))

    # ──── 2. 计算加权总分 ────
    total_score = 0.0
    buy_score_sum = 0.0
    against_score_sum = 0.0
    agent_votes: dict[str, dict[str, float]] = {}

    for output in outputs:
        agent_name = output.agent_name.value
        agent_weight = weight_map.get(agent_name, 0.25)

        # [PRD-T-097] 极端评分权重减半
        if output.is_extreme:
            agent_weight *= 0.5

        effective_score = output.score * agent_weight
        total_score += effective_score

        # [PRD-T-102] [PRD-T-103] 买入理由 vs 反对理由
        buy_reason_count = max(len(output.buy_reasons), 1)
        against_reason_count = max(len(output.against_reasons), 1)

        # 避免除零
        total_ratio = buy_reason_count + against_reason_count
        buy_weight_ratio = buy_reason_count / total_ratio
        against_weight_ratio = against_reason_count / total_ratio

        buy_score_sum += output.score * buy_weight_ratio * agent_weight
        against_score_sum += (100 - output.score) * against_weight_ratio * agent_weight

        agent_votes[agent_name] = {
            "score": output.score,
            "weight": round(agent_weight, 4),
            "effective_score": round(effective_score, 2),
        }

    # ──── 3. 归一化 ────
    weight_sum = sum(v["weight"] for v in agent_votes.values())
    if weight_sum > 0:
        normalized_factor = 4.0 / weight_sum  # 归一化到4个Agent
        total_score *= normalized_factor
        buy_score_sum *= normalized_factor
        against_score_sum *= normalized_factor

    # ──── 4. 计算净分 ────
    net_score = buy_score_sum - against_score_sum

    # ──── 5. 决策判定 [PRD-T-103] ────
    if net_score > decision_threshold:
        decision = DecisionType.BUY
        decision_reason = (
            f"买入理由加权总分{buy_score_sum:.1f}高于反对理由{against_score_sum:.1f}，"
            f"净分{net_score:.1f}超阈值{decision_threshold}"
        )
    elif net_score > 0:
        decision = DecisionType.HOLD
        decision_reason = (
            f"买入理由略高于反对理由，但净分{net_score:.1f}未达阈值{decision_threshold}"
        )
    else:
        decision = DecisionType.REJECT
        decision_reason = (
            f"反对理由加权总分{against_score_sum:.1f}高于买入理由{buy_score_sum:.1f}"
        )

    # ──── 6. 风控否决检查 [PRD-T-101] ────
    risk_veto = False
    risk_veto_reason: str | None = None

    # 6a. 极端行情一票否决
    if market_state == "extreme":
        risk_veto = True
        risk_veto_reason = "极端行情，风控一票否决"
        decision = DecisionType.REJECT

    # 6b. 未解决风控事件
    if risk_events_active:
        risk_veto = True
        risk_veto_reason = "存在未解决风控事件"
        decision = DecisionType.REJECT

    # 6c. 流动性检查
    if daily_volume is not None and daily_volume < min_daily_volume:
        risk_veto = True
        risk_veto_reason = f"日均成交额{daily_volume:.0f}低于最低阈值{min_daily_volume:.0f}"
        decision = DecisionType.REJECT

    return WeightedVoteResult(
        stock_code=stock_code,
        total_score=round(total_score, 2),
        buy_score_sum=round(buy_score_sum, 2),
        against_score_sum=round(against_score_sum, 2),
        net_score=round(net_score, 2),
        decision=decision,
        risk_veto=risk_veto,
        risk_veto_reason=risk_veto_reason,
        agent_votes=agent_votes,
        convergence_method=convergence_method,
    )


def find_extreme_market_state(weights: list[dict[str, Any]]) -> str | None:
    """查找权重配置中是否存在极端行情状态"""
    for w in weights:
        if w.get("market_state") == "extreme":
            return "extreme"
    return None
