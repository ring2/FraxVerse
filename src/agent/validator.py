"""
FraxVerse · Agent 输出校验器与不收敛兜底处理

严格按 DD-04-AI-Agent模块.md 第4.7~4.8节实现。

校验规则：
- [PRD-T-095] 评分不在0-100 → 无效不参与投票
- [PRD-T-096] 反对理由为空 → 评分强制降为50
- [PRD-T-097] 极端评分(0/100) → 权重减半（标记 is_extreme）
- [PRD-T-098] 不收敛(分歧>30) → trimmed mean
- [PRD-T-099] 持续极端(连续5次) → 降权50%+告警
"""
from __future__ import annotations

import logging
from statistics import mean
from typing import Any

from src.agent.models import AgentOutput

logger = logging.getLogger(__name__)


def validate_agent_outputs(outputs: list[AgentOutput]) -> list[AgentOutput]:
    """
    校验每个Agent的输出，对异常情况进行兜底处理。

    对应 DD-04 第4.7节 validate_agent_outputs 伪代码。
    """
    validated: list[AgentOutput] = []

    for output in outputs:
        # ──── 校验1: 评分不在0-100 → 无效不参与投票 [PRD-T-095] ────
        if not (0 <= output.score <= 100):
            logger.warning("Agent %s 评分 %d 不在0-100范围，标记无效", output.agent_name, output.score)
            validated.append(output)
            continue

        # ──── 校验2: 反对理由为空 → 评分强制降为50 [PRD-T-096] ────
        if output.has_no_against_reasons:
            original_score = output.score
            output.score = 50  # 证伪机制底线
            logger.warning(
                "Agent %s 反对理由为空，评分从 %d 强制降为50",
                output.agent_name, original_score,
            )

        # ──── 校验4: 买入理由为空 → 评分也降为50 ────
        if len(output.buy_reasons) == 0:
            output.score = 50
            logger.warning("Agent %s 买入理由为空，评分降为50", output.agent_name)

        validated.append(output)

    return validated


def handle_no_convergence(scores: list[int]) -> tuple[float, str]:
    """
    处理讨论不收敛的情况（DD-04 第4.8节）。

    [PRD-T-098] 不收敛(分歧>30) → trimmed mean

    返回: (最终分数, 收敛方法)
    """
    if len(scores) < 2:
        return (mean(scores) if scores else 0, "insufficient_data")

    max_diff = max(scores) - min(scores)

    if max_diff <= 30:
        # 已收敛
        return (mean(scores), "normal")

    # 不收敛：丢弃最高分和最低分，取 trimmed mean [PRD-T-098]
    sorted_scores = sorted(scores)
    trimmed = sorted_scores[1:-1]  # 去掉最高和最低

    if len(trimmed) == 0:
        # 只有2个有效评分，无法 trimmed，取均值
        trimmed = scores

    final_score = mean(trimmed)
    logger.warning("讨论不收敛(max_diff=%d)，采用trimmed mean: %.1f", max_diff, final_score)

    return (final_score, "trimmed_mean")


def check_convergence(outputs: list[AgentOutput]) -> tuple[bool, float, list[AgentOutput]]:
    """
    检查一组 Agent 输出是否收敛。

    收敛定义：所有有效评分分差 ≤ 30。

    返回: (is_converged, max_score_diff, validated_outputs)
    """
    validated = validate_agent_outputs(outputs)

    valid_scores = [o.score for o in validated if 0 <= o.score <= 100]
    if len(valid_scores) < 2:
        return (False, 0, validated)

    max_diff = max(valid_scores) - min(valid_scores)
    is_converged = max_diff <= 30

    return (is_converged, max_diff, validated)


def check_extreme_streak(
    outputs: list[AgentOutput],
    get_recent_scores_fn: callable | None = None,
) -> list[dict[str, Any]]:
    """
    检查Agent是否持续给出极端评分。

    [PRD-T-099] 连续5次极端评分 → 降权50%+告警

    get_recent_scores_fn: 用于从 DB 查询历史评分的回调函数。
        签名: fn(agent_name: str) -> list[int]
        None 时使用默认检查（只检查本轮）。

    返回: 告警列表 [{agent_name, extreme_count, action}]
    """
    alerts: list[dict[str, Any]] = []
    seen_agents = set()

    for output in outputs:
        if output.agent_name.value in seen_agents:
            continue
        seen_agents.add(output.agent_name.value)

        # 查询该Agent最近5次评分
        recent_scores: list[int] = [output.score]
        if get_recent_scores_fn:
            try:
                recent_scores = get_recent_scores_fn(output.agent_name.value)
            except Exception as e:
                logger.warning("Failed to get recent scores for %s: %s", output.agent_name, e)

        extreme_count = sum(1 for s in recent_scores if s in (0, 100))

        if extreme_count >= 5:
            logger.warning(
                "Agent %s 连续 %d 次极端评分，需降权50%",
                output.agent_name, extreme_count,
            )
            alerts.append({
                "agent_name": output.agent_name.value,
                "extreme_count": extreme_count,
                "action": "degrade_50pct",
            })
        elif extreme_count > 0:
            alerts.append({
                "agent_name": output.agent_name.value,
                "extreme_count": extreme_count,
                "action": "update_count",
            })

    return alerts
