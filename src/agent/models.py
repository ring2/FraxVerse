"""
FraxVerse · AI-Agent 模块 — Pydantic 结构化输出模型

来源：DD-04-AI-Agent模块.md 第2.3节
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AgentName(str, Enum):
    """四位Agent枚举"""
    MAINLINE_HUNTER = "mainline_hunter"       # 主线猎手
    FUND_DETECTIVE = "fund_detective"          # 资金侦探
    SENTIMENT_CATCHER = "sentiment_catcher"    # 情绪捕手
    EXPERIENCE_JUDGE = "experience_judge"      # 经验法官


class PredictedOutcome(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    AVOID = "avoid"


class DecisionType(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    REJECT = "reject"


class AgentOutput(BaseModel):
    """单个Agent对单只股票的分析输出 [PRD-T-093]"""
    agent_name: AgentName
    score: int = Field(ge=0, le=100, description="评分0-100")
    buy_reasons: list[str] = Field(description="买入理由，至少1条")
    against_reasons: list[str] = Field(description="反对理由，至少1条")  # [PRD-T-102]
    confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="信心度")
    predicted_outcome: PredictedOutcome = Field(default=PredictedOutcome.HOLD)
    supplement: Optional[str] = None

    @field_validator("score")
    @classmethod
    def score_must_be_valid(cls, v: int) -> int:
        if not (0 <= v <= 100):  # [PRD-T-095] 评分不在0-100→无效
            raise ValueError(f"Score {v} out of range [0, 100]")
        return v

    @property
    def is_extreme(self) -> bool:
        """极端评分检查 [PRD-T-097]"""
        return self.score in (0, 100)

    @property
    def has_no_against_reasons(self) -> bool:
        """反对理由为空检查 [PRD-T-096]"""
        return len(self.against_reasons) == 0


class AgentDiscussionRound(BaseModel):
    """一轮讨论结果"""
    round_num: int = Field(ge=1, le=3)
    stock_code: str
    outputs: list[AgentOutput]
    max_score_diff: float = Field(description="本轮最大分差")
    is_converged: bool = Field(description="是否已收敛(分差<=30)")


class WeightedVoteResult(BaseModel):
    """加权投票结果 [PRD-T-100~T-103]"""
    stock_code: str
    total_score: float
    buy_score_sum: float  # [PRD-T-103]
    against_score_sum: float
    net_score: float
    decision: DecisionType
    risk_veto: bool = False  # [PRD-T-101]
    risk_veto_reason: Optional[str] = None
    agent_votes: dict[str, dict]  # {agent_name: {score, weight, effective_score}}
    convergence_method: str = "normal"  # normal/trimmed_mean/degraded


class LLMCallRecord(BaseModel):
    """单次LLM调用记录 [PRD-T-112]"""
    model: str
    agent_name: str
    stock_code: str
    prompt_tokens: int
    completion_tokens: int
    total_cost: float
    latency_ms: int
    is_success: bool
    error_message: Optional[str] = None


class DegradeLevel(str, Enum):
    """LLM降级等级 [PRD-T-113]"""
    NONE = "none"
    LIGHT = "light"       # 2轮讨论
    PARTIAL = "partial"   # 1轮+跳过非核心标的
    FULL = "full"         # 完全降级纯规则
