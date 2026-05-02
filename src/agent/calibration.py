"""
FraxVerse · 权重自动校准

严格按 DD-04-AI-Agent模块.md 第4.10节实现。

核心约束：
- [PRD-T-104] 滚动胜率：最近20次推荐统计
- [PRD-T-105] 胜率<40%→降权50%；>70%→提升20%(上限130%)
- [PRD-T-106] 校准系数上限1.3，下限0.3
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# 市场状态列表（权重需归一化）
MARKET_STATES = ["mainline_confirmed", "oscillating"]

# 胜率→校准系数映射 [PRD-T-105]
WINRATE_TO_CALIB: list[tuple[float, float]] = [
    (0.70, 1.3),   # 胜率≥70%→1.3（提升20%，上限130%）
    (0.60, 1.1),   # 60%≤胜率<70%→1.1（微升）
    (0.50, 1.0),   # 50%≤胜率<60%→1.0（不变）
    (0.40, 0.7),   # 40%≤胜率<50%→0.7（降低）
    (0.00, 0.5),   # 胜率<40%→0.5（大幅降低）
]


def get_calib_factor(win_rate: float) -> float:
    """
    根据胜率计算校准系数 [PRD-T-105]。

    Args:
        win_rate: 滚动胜率 (0.0 - 1.0)

    Returns:
        校准系数（受 [PRD-T-106] 边界约束 0.3~1.3）
    """
    for threshold, factor in WINRATE_TO_CALIB:
        if win_rate >= threshold:
            calib = factor
            break
    else:
        calib = 0.5

    # [PRD-T-106] 校准系数边界钳位
    return max(0.3, min(1.3, calib))


def calibrate_weights(
    date: str,
    get_agent_history_fn: Callable[[str], list[dict[str, Any]]],
    get_all_weights_fn: Callable[[str], list[dict[str, Any]]],
    update_weight_fn: Callable[[str, str, float, float, float, int], None],
) -> list[dict[str, Any]]:
    """
    每日投票前执行权重校准，使用截止到昨日的数据。

    对应 DD-04 第4.10节 calibrate_weights 伪代码。

    Args:
        date: 当前日期
        get_agent_history_fn: 查询Agent历史记录的函数
            签名: fn(agent_name: str) -> list[dict]
            返回值: [{"predicted_outcome": "buy", "actual_outcome": "win"}, ...]
        get_all_weights_fn: 查询某市场状态下所有权重的函数
            签名: fn(market_state: str) -> list[dict]
            返回值: [{"id": 1, "agent_name": "...", "effective_weight": 0.35, ...}]
        update_weight_fn: 更新权重的函数
            签名: fn(agent_name: str, market_state: str, calib_factor: float,
                     effective_weight: float, win_rate: float, recent_count: int) -> None

    Returns:
        校准日志列表 [{agent_name, win_rate, calib_factor, old_effective, new_effective}]
    """
    agent_names = ["mainline_hunter", "fund_detective", "sentiment_catcher", "experience_judge"]
    calibration_log: list[dict[str, Any]] = []

    for agent_name in agent_names:
        # ──── 1. 计算滚动胜率 [PRD-T-104] ────
        recent_records = get_agent_history_fn(agent_name)

        if not recent_records:
            logger.info("Agent %s 无历史数据，保持默认权重", agent_name)
            continue

        win_count = sum(
            1 for r in recent_records
            if r.get("predicted_outcome") == "buy" and r.get("actual_outcome") == "win"
        )
        total_count = sum(
            1 for r in recent_records
            if r.get("predicted_outcome") == "buy"
        )

        if total_count == 0:
            win_rate = 0.5  # 无推荐记录，默认0.5
        else:
            win_rate = win_count / total_count

        # ──── 2. 计算校准系数 [PRD-T-105] ────
        calib_factor = get_calib_factor(win_rate)

        # ──── 3. 更新所有市场状态下的权重 ────
        for ms in MARKET_STATES:
            current_weights = get_all_weights_fn(ms)

            # 找到该Agent的当前记录
            current = None
            for w in current_weights:
                if w.get("agent_name") == agent_name:
                    current = w
                    break

            if current is None:
                logger.warning("Agent %s 在市场状态 %s 下无权重记录", agent_name, ms)
                continue

            old_effective = float(current.get("effective_weight", 0))
            base_weight = float(current.get("base_weight", 0.25))
            new_effective = base_weight * calib_factor

            # 更新数据库
            update_weight_fn(agent_name, ms, calib_factor, new_effective, win_rate, total_count)

            calibration_log.append({
                "agent_name": agent_name,
                "market_state": ms,
                "win_rate": round(win_rate, 4),
                "calib_factor": calib_factor,
                "old_effective": old_effective,
                "new_effective": new_effective,
            })

        logger.info("Agent %s 校准: 胜率=%.2f%%, 校准系数=%.2f", agent_name, win_rate * 100, calib_factor)

    # ──── 4. 归一化有效权重 ────
    normalize_weights(MARKET_STATES, get_all_weights_fn, update_weight_fn)

    return calibration_log


def normalize_weights(
    market_states: list[str],
    get_all_weights_fn: Callable[[str], list[dict[str, Any]]],
    update_weight_fn: Callable[[str, str, float, float, float, int], None],
) -> None:
    """
    归一化同一市场状态下所有Agent的有效权重，使总和=1.0。

    对应 DD-04 第4.10节 normalize_weights 伪代码。
    """
    for ms in market_states:
        all_weights = get_all_weights_fn(ms)
        weight_sum = sum(float(w.get("effective_weight", 0)) for w in all_weights)

        if weight_sum <= 0:
            logger.warning("市场状态 %s 的权重和为0，跳过归一化", ms)
            continue

        for w in all_weights:
            normalized = float(w.get("effective_weight", 0)) / weight_sum
            agent_name = w.get("agent_name", "")
            # 保持 calib_factor 和 win_rate 不变，只更新 effective_weight
            update_weight_fn(
                agent_name, ms,
                float(w.get("calib_factor", 1.0)),
                round(normalized, 4),
                float(w.get("win_rate", 0.5)),
                int(w.get("recent_count", 0)),
            )
