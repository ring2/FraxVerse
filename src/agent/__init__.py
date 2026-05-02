"""
FraxVerse · AI-Agent 智能订阅员决策模块

严格按 DD-04-AI-Agent模块.md 实现。
"""
from src.agent.models import (
    AgentName,
    AgentOutput,
    AgentDiscussionRound,
    WeightedVoteResult,
    LLMCallRecord,
    PredictedOutcome,
    DecisionType,
    DegradeLevel,
)
from src.agent.llm_client import (
    build_agent_input,
    call_single_agent,
    call_agents_concurrently,
    render_prompt_template,
)
from src.agent.validator import (
    validate_agent_outputs,
    check_convergence,
    handle_no_convergence,
    check_extreme_streak,
)
from src.agent.voting import weighted_vote
from src.agent.calibration import calibrate_weights, get_calib_factor
from src.agent.budget import (
    check_llm_budget,
    record_token_usage,
    get_budget_status,
    get_degrade_level,
)
from src.agent.degradation import (
    generate_rule_based_decisions,
    generate_fallback_decision,
)
from src.agent.orchestrator import AgentOrchestrator

__all__ = [
    "AgentName",
    "AgentOutput",
    "AgentDiscussionRound",
    "WeightedVoteResult",
    "LLMCallRecord",
    "PredictedOutcome",
    "DecisionType",
    "DegradeLevel",
    "build_agent_input",
    "call_single_agent",
    "call_agents_concurrently",
    "render_prompt_template",
    "validate_agent_outputs",
    "check_convergence",
    "handle_no_convergence",
    "check_extreme_streak",
    "weighted_vote",
    "calibrate_weights",
    "get_calib_factor",
    "check_llm_budget",
    "record_token_usage",
    "get_budget_status",
    "get_degrade_level",
    "generate_rule_based_decisions",
    "generate_fallback_decision",
    "AgentOrchestrator",
]
