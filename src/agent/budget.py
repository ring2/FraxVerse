"""
FraxVerse · Token 用量监控与预算控制

严格按 DD-04-AI-Agent模块.md 第4.11节实现。

核心约束：
- [PRD-T-112] LLM token计数器，每次记录prompt+completion tokens
- [PRD-T-113] 日/月Token预算上限，超限降级
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Callable

import redis

from src.config import settings
from src.agent.models import DegradeLevel, LLMCallRecord

logger = logging.getLogger(__name__)

# 预算默认配置
DEFAULT_DAILY_LIMIT = 100_000       # 日Token预算
DEFAULT_MONTHLY_LIMIT = 2_000_000   # 月Token预算


def _get_redis() -> redis.Redis:
    """获取 Redis 连接"""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def estimate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """估算LLM调用成本（元）[PRD-T-112]"""
    # 参考价格（2026年5月，元/千token）
    price_table: dict[str, dict[str, float]] = {
        "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
        "deepseek-v3": {"prompt": 0.001, "completion": 0.002},
        "glm-4-flash": {"prompt": 0.001, "completion": 0.002},
        "claude-sonnet": {"prompt": 0.021, "completion": 0.105},
        "gpt-4o": {"prompt": 0.0175, "completion": 0.07},
    }
    price = price_table.get(model, price_table["deepseek-chat"])
    cost = (prompt_tokens / 1000 * price["prompt"]) + (completion_tokens / 1000 * price["completion"])
    return cost


def record_token_usage(
    model: str,
    agent_name: str,
    stock_code: str,
    prompt_tokens: int,
    completion_tokens: int,
    is_success: bool = True,
    error_message: str | None = None,
    latency_ms: int = 0,
    update_db_fn: Callable | None = None,
) -> LLMCallRecord:
    """
    记录单次LLM调用的Token用量（DD-04 第4.11节 record_token_usage）。

    [PRD-T-112] 每次记录 prompt+completion tokens

    Args:
        update_db_fn: 更新 llm_usage 表的回调函数。
            签名: fn(model, agent_name, date, prompt_tokens, completion_tokens, cost, call_count) -> None
            None 时只更新 Redis 计数器。
    """
    cost = estimate_llm_cost(model, prompt_tokens, completion_tokens)
    today = date.today()

    # 更新 Redis 实时计数器
    try:
        r = _get_redis()
        r.incrby(f"llm:daily:{today.isoformat()}:prompt_tokens", prompt_tokens)
        r.incrby(f"llm:daily:{today.isoformat()}:completion_tokens", completion_tokens)
        r.incrby(f"llm:monthly:{today.strftime('%Y-%m')}:total_tokens", prompt_tokens + completion_tokens)
    except Exception as e:
        logger.warning("Redis token counter update failed: %s", e)

    # 更新数据库（如果有回调）
    if update_db_fn:
        try:
            update_db_fn(model, agent_name, today, prompt_tokens, completion_tokens, cost, 1)
        except Exception as e:
            logger.error("Database token usage update failed: %s", e)

    # 检查预算并触发降级
    check_budget_and_degrade_if_needed(
        daily_limit=DEFAULT_DAILY_LIMIT,
        monthly_limit=DEFAULT_MONTHLY_LIMIT,
    )

    return LLMCallRecord(
        model=model,
        agent_name=agent_name,
        stock_code=stock_code,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_cost=round(cost, 4),
        latency_ms=latency_ms,
        is_success=is_success,
        error_message=error_message,
    )


def check_llm_budget(
    daily_limit: int = DEFAULT_DAILY_LIMIT,
    monthly_limit: int = DEFAULT_MONTHLY_LIMIT,
) -> bool:
    """
    检查Token预算是否充足（DD-04 第4.11节 check_llm_budget）。

    [PRD-T-113] 日/月Token预算上限，超限降级

    Returns:
        True = 预算充足，False = 预算超限
    """
    today = date.today()

    try:
        r = _get_redis()

        # 查询当日用量
        daily_used_str = r.get(f"llm:daily:{today.isoformat()}:total_tokens")
        daily_used = int(daily_used_str) if daily_used_str else 0

        # 查询当月用量
        monthly_used_str = r.get(f"llm:monthly:{today.strftime('%Y-%m')}:total_tokens")
        monthly_used = int(monthly_used_str) if monthly_used_str else 0

        if daily_used >= daily_limit:
            logger.warning("日Token预算超限: %d/%d", daily_used, daily_limit)
            return False

        if monthly_used >= monthly_limit:
            logger.warning("月Token预算超限: %d/%d", monthly_used, monthly_limit)
            return False

        return True

    except Exception as e:
        logger.warning("Budget check failed (Redis unavailable): %s", e)
        # Redis 不可用时默认允许（降级不因基础设施问题拒绝）
        return True


def check_budget_and_degrade_if_needed(
    daily_limit: int = DEFAULT_DAILY_LIMIT,
    monthly_limit: int = DEFAULT_MONTHLY_LIMIT,
) -> DegradeLevel:
    """
    Token超限时的降级策略（DD-04 第4.11节 check_budget_and_degrade_if_needed）。

    [PRD-T-113] 超限降级：减少Agent讨论轮数或跳过部分标的

    Returns:
        当前降级等级
    """
    today = date.today()

    try:
        r = _get_redis()

        daily_used_str = r.get(f"llm:daily:{today.isoformat()}:total_tokens")
        daily_used = int(daily_used_str) if daily_used_str else 0
        usage_ratio = daily_used / daily_limit if daily_limit > 0 else 0

        degrade_level: DegradeLevel
        if usage_ratio >= 1.0:
            # 超限：完全降级为纯规则模式
            degrade_level = DegradeLevel.FULL
            logger.warning("Token预算已用完(%d/%d)，完全降级为纯规则模式", daily_used, daily_limit)
        elif usage_ratio >= 0.8:
            # 接近超限：减少讨论轮数到1轮，跳过部分标的
            degrade_level = DegradeLevel.PARTIAL
            logger.warning("Token预算使用%.0f%%(%d/%d)，部分降级", usage_ratio * 100, daily_used, daily_limit)
        elif usage_ratio >= 0.6:
            # 轻度降级：讨论轮数减为2轮
            degrade_level = DegradeLevel.LIGHT
            logger.info("Token预算使用%.0f%%(%d/%d)，轻度降级", usage_ratio * 100, daily_used, daily_limit)
        else:
            degrade_level = DegradeLevel.NONE

        r.set("llm:degrade_level", degrade_level.value)
        return degrade_level

    except Exception as e:
        logger.warning("Budget degrade check failed: %s", e)
        return DegradeLevel.NONE


def get_degrade_level() -> DegradeLevel:
    """获取当前降级等级"""
    try:
        r = _get_redis()
        level = r.get("llm:degrade_level")
        if level:
            return DegradeLevel(level)
    except Exception:
        pass
    return DegradeLevel.NONE


def get_budget_status(daily_limit: int = DEFAULT_DAILY_LIMIT) -> dict[str, Any]:
    """
    获取预算状态（用于 API 响应）。

    Returns:
        {
            "daily_limit": 100000,
            "daily_used": 65000,
            "monthly_limit": 2000000,
            "monthly_used": 800000,
            "is_over_budget": False,
            "degrade_level": "none"
        }
    """
    today = date.today()
    month_key = today.strftime("%Y-%m")

    try:
        r = _get_redis()
        daily_used_str = r.get(f"llm:daily:{today.isoformat()}:total_tokens")
        monthly_used_str = r.get(f"llm:monthly:{month_key}:total_tokens")
        daily_used = int(daily_used_str) if daily_used_str else 0
        monthly_used = int(monthly_used_str) if monthly_used_str else 0
    except Exception:
        daily_used = 0
        monthly_used = 0

    return {
        "daily_limit": daily_limit,
        "daily_used": daily_used,
        "monthly_limit": DEFAULT_MONTHLY_LIMIT,
        "monthly_used": monthly_used,
        "is_over_budget": daily_used >= daily_limit or monthly_used >= DEFAULT_MONTHLY_LIMIT,
        "degrade_level": get_degrade_level().value,
    }
