"""
FraxVerse · LLM 降级策略

严格按 DD-04-AI-Agent模块.md 第4.12节实现。

核心约束：
- [PRD-T-111] Agent可插拔增强组件，LLM故障降级纯规则
- [PRD-T-108] 全部超时降级评分层
"""
from __future__ import annotations

import logging
from typing import Any

from src.agent.models import DecisionType, WeightedVoteResult

logger = logging.getLogger(__name__)

# 纯规则模式默认阈值
DEFAULT_BUY_THRESHOLD = 70    # 评分 >= 70 → buy
DEFAULT_HOLD_THRESHOLD = 50   # 评分 >= 50 → hold
                              # 评分 < 50 → reject


def generate_rule_based_decisions(
    stock_pool: list[dict[str, Any]],
    date: str,
    buy_threshold: float = DEFAULT_BUY_THRESHOLD,
    hold_threshold: float = DEFAULT_HOLD_THRESHOLD,
) -> list[WeightedVoteResult]:
    """
    LLM不可用时的纯规则降级模式（DD-04 第4.12节）。

    [PRD-T-111] LLM故障降级纯规则
    直接使用 DD-03 评分层的结果作为决策依据。

    Args:
        stock_pool: 股票池记录列表 [{stock_code, score_total, ...}]
        date: 当前日期
        buy_threshold: 买入阈值
        hold_threshold: 观望阈值

    Returns:
        决策结果列表
    """
    decisions: list[WeightedVoteResult] = []

    for pool in stock_pool:
        stock_code = pool.get("stock_code", "")
        score_total = float(pool.get("score_total", 0))

        if score_total >= buy_threshold:
            decision_type = DecisionType.BUY
            reason = f"纯规则模式: 评分{score_total:.1f}超过买入阈值{buy_threshold}"
        elif score_total >= hold_threshold:
            decision_type = DecisionType.HOLD
            reason = f"纯规则模式: 评分{score_total:.1f}处于观望区间"
        else:
            decision_type = DecisionType.REJECT
            reason = f"纯规则模式: 评分{score_total:.1f}低于观望阈值{hold_threshold}"

        decisions.append(WeightedVoteResult(
            stock_code=stock_code,
            total_score=score_total,
            buy_score_sum=score_total,
            against_score_sum=0.0,
            net_score=score_total,
            decision=decision_type,
            agent_votes={},
            convergence_method="degraded_rule",
        ))

    logger.info("纯规则降级模式生成 %d 条决策", len(decisions))
    return decisions


def generate_fallback_decision(
    stock_code: str,
    score_total: float | None,
    date: str,
) -> WeightedVoteResult:
    """
    单只标的讨论失败时的降级决策（DD-04 第4.12节 generate_fallback_decision）。

    用评分层分值作为替补。

    Args:
        stock_code: 股票代码
        score_total: DD-03 评分层总分（None = 数据不可用）
        date: 当前日期
    """
    if score_total is not None:
        decision = DecisionType.BUY if score_total >= 70 else DecisionType.REJECT
    else:
        decision = DecisionType.REJECT
        score_total = 0.0

    return WeightedVoteResult(
        stock_code=stock_code,
        total_score=score_total,
        buy_score_sum=score_total,
        against_score_sum=0.0,
        net_score=score_total,
        decision=decision,
        agent_votes={},
        convergence_method="degraded_single",
    )
