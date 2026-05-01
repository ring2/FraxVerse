"""Agent 相关 Schemas"""
from datetime import date, datetime

from pydantic import BaseModel


class AgentDiscussionItem(BaseModel):
    id: int
    date: date
    stock_code: str
    agent_name: str
    round_num: int
    score: int | None = None
    confidence: float | None = None
    buy_reasons: list[str] = []
    against_reasons: list[str] = []
    created_at: datetime


class AgentWeightItem(BaseModel):
    agent_name: str
    market_state: str
    base_weight: float
    effective_weight: float
    win_rate: float | None = None


class LLMUsageItem(BaseModel):
    date: date
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0
    call_count: int = 0
