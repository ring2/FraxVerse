# DD-04 · AI-Agent 模块

> 碎片宇宙（FraxVerse）智能量化交易系统 · 详细设计文档
> 版本：V1.0 | 创建：2026-05-01
> 公共约定引用：[DD-00-文档规范与公共约定](./DD-00-文档规范与公共约定.md)
> FraxVerse命名：Agent→「碎片聚合」 | Agent讨论→「心念碰撞」 | 证伪机制→「内观之镜」

---

## 编写前必覆盖清单（源自 TRACE-MATRIX.md）

- [x] T-090: L2513 Agent编排 — 选TradingAgents Fork
- [x] T-091: L2520 Fork TradingAgents → 替换4个Agent提示词 → 接入A股数据源
- [x] T-092: L2448 原生辩论机制：Bull/Bear多轮辩论
- [x] T-093: L2450 结构化输出：Pydantic模型
- [x] T-094: L285 多轮讨论2-3轮收敛
- [x] T-095: L293 评分不在0-100→无效不参与投票
- [x] T-096: L294 反对理由为空→评分强制降为50
- [x] T-097: L295 极端评分(0/100)→权重减半
- [x] T-098: L296 不收敛(分歧>30)→trimmed mean
- [x] T-099: L297 持续极端(连续5次)→降权50%+告警
- [x] T-100: L328 权重动态分配：主线明确vs震荡市
- [x] T-101: L330 极端行情：风控一票否决
- [x] T-102: L945 每个Agent必须输出买入理由+反对理由
- [x] T-103: L954 买入理由总分>反对理由总分+阈值才开仓
- [x] T-104: L922 滚动胜率：最近20次推荐统计
- [x] T-105: L923 胜率<40%→降权50%；>70%→提升20%(上限130%)
- [x] T-106: L938 校准系数上限1.3，下限0.3
- [x] T-107: L986 asyncio+aiohttp并发调用LLM，串行禁止
- [x] T-108: L993 超时60秒跳过该Agent；全部超时降级评分层
- [x] T-109: L1015 Agent聚焦定性判断，定量由评分层处理
- [x] T-110: L1028 不用Agent算数学、不让Agent读K线
- [x] T-111: L2556 Agent可插拔增强组件，LLM故障降级纯规则
- [x] T-112: L2668 LLM token计数器，每次记录prompt+completion tokens
- [x] T-113: L2670 日/月Token预算上限，超限降级

---

## 1. 模块概述

### 1.1 职责边界

本模块负责：

- TradingAgents 框架 Fork 改造与4个自定义Agent的实现 [PRD-T-090] [PRD-T-091]
- Agent 原生辩论机制调度（2-3轮多轮讨论收敛） [PRD-T-092] [PRD-T-094]
- Agent 结构化输出校验（Pydantic模型 + 输出校验器） [PRD-T-093]
- Agent 输出异常兜底（评分越界/反对理由为空/极端评分/不收敛） [PRD-T-095~T-099]
- 加权投票决策（动态权重分配 + 风控一票否决） [PRD-T-100] [PRD-T-101]
- 证伪机制（每个Agent必须输出买入理由+反对理由） [PRD-T-102] [PRD-T-103]
- 滚动胜率跟踪与权重自动校准 [PRD-T-104~T-106]
- LLM 异步并发调用与超时降级 [PRD-T-107] [PRD-T-108]
- Agent 输入优化（聚焦定性判断，不读K线/不算数学） [PRD-T-109] [PRD-T-110]
- Agent 可插拔降级（LLM故障→纯规则模式） [PRD-T-111]
- LLM Token 用量监控与预算控制 [PRD-T-112] [PRD-T-113]

**不负责**：

- 粗筛+评分引擎（见 DD-03）
- 下单执行（见 DD-05）
- 止损/止盈监控（见 DD-05/DD-06）
- 新闻/数据采集（见 DD-02）
- 经验库存储与匹配（见 DD-07，但本模块读取经验库作为经验法官输入）
- 前端展示（见 DD-08）

### 1.2 依赖关系

```
DD-04 AI-Agent 模块
  ├── 依赖 DD-02 — news / sector_data / fund_flows / macroeconomic (Agent输入数据)
  ├── 依赖 DD-03 — stock_pool(评分结果) / market_state_log(市场状态) / strategy_params
  ├── 依赖 DD-07 — experiences(经验法官匹配) / param_change_log
  ├── 依赖 TradingAgents — 辩论框架 Fork [PRD-T-090]
  ├── 依赖 LLM API — DeepSeek V3 / GLM-4 Flash / Claude / GPT-4o
  ├── 依赖 Redis — Agent权重缓存 / Token预算计数 / 降级状态
  └── 被依赖 — DD-05交易执行(决策结果) / DD-06风控(风控否决) / DD-08前端(Agent讨论页)
```

### 1.3 模块定位

```
┌──────────────────────────────────────────────────────────┐
│                    四层漏斗筛选流程                        │
├──────────────────────────────────────────────────────────┤
│  第一层：粗筛（DD-03）        — 规则引擎，不依赖LLM       │
│  第二层：评分（DD-03）        — 规则引擎，不依赖LLM       │
│  第三层：Agent分析（DD-04）   — ★本模块★，LLM驱动        │
│  第四层：加权投票+风控（DD-04）— ★本模块★，纯逻辑        │
├──────────────────────────────────────────────────────────┤
│  关键原则：P0阶段不依赖LLM，纯规则模式即可运行            │  # PRD L2539 强约束
│  Agent是可插拔增强组件——有它更好，没它系统照样跑           │  # PRD L2556 强约束
└──────────────────────────────────────────────────────────┘
```

### 1.4 FraxVerse 品牌映射

| 通用术语 | FraxVerse命名 | 释义 |
|:---------|:-------------|:-----|
| Agent | 碎片聚合 | 四位Agent如同碎片聚合成的智慧体 |
| Agent讨论 | 心念碰撞 | Agent间的辩论如同心念碰撞出真知 |
| 证伪机制 | 内观之镜 | 强制输出反对理由如同内观自省 |
| 权重校准 | 心念调谐 | 根据历史胜率调谐Agent影响力 |
| 降级模式 | 静默模式 | LLM故障时回归纯规则的静默运行 |

---

## 2. 核心数据模型

### 2.1 数据库表设计

> Schema所有权：本节定义的表为权威DDL，其他模块引用时标注来源。

#### 2.1.1 agent_discussions 表 — Agent讨论记录

```sql
-- [Schema所有权: DD-04] 权威定义
CREATE TABLE agent_discussions (
    id              BIGSERIAL       PRIMARY KEY,
    date            DATE            NOT NULL,                       -- 讨论日期
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code), -- 标的
    round_num       SMALLINT        NOT NULL DEFAULT 1,             -- 讨论轮次(1-3)
    agent_name      VARCHAR(32)     NOT NULL,                       -- Agent名称
    -- 结构化输出 [PRD-T-093]
    score           SMALLINT,                                       -- Agent评分 0-100
    buy_reasons     JSONB           NOT NULL DEFAULT '[]',          -- 买入理由数组
    against_reasons JSONB           NOT NULL DEFAULT '[]',          -- 反对理由数组 [PRD-T-102]
    confidence      NUMERIC(4,2)    DEFAULT 0.5,                    -- 信心度 0-1
    -- 元数据
    prompt_tokens   INTEGER         DEFAULT 0,                      -- [PRD-T-112]
    completion_tokens INTEGER       DEFAULT 0,                      -- [PRD-T-112]
    model_name      VARCHAR(32),                                    -- 使用的LLM模型
    is_valid        BOOLEAN         NOT NULL DEFAULT TRUE,          -- 校验后是否有效
    invalid_reason  VARCHAR(64),                                    -- 无效原因
    -- 校准追踪 [PRD-T-104]
    predicted_outcome VARCHAR(16),                                  -- buy/hold/avoid
    actual_outcome  VARCHAR(16),                                    -- win/loss/pending
    outcome_updated_at TIMESTAMPTZ,                                 -- 实际结果更新时间
    -- 通用字段
    raw_response    TEXT,                                           -- LLM原始响应(调试用)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 复合索引：按日期+标的查询讨论记录
CREATE INDEX idx_agent_disc_date_stock ON agent_discussions(date DESC, stock_code);
-- 按Agent名称查询历史推荐
CREATE INDEX idx_agent_disc_agent ON agent_discussions(agent_name, date DESC);
-- 按预测结果查询(胜率统计)
CREATE INDEX idx_agent_disc_outcome ON agent_discussions(predicted_outcome, actual_outcome)
    WHERE predicted_outcome IS NOT NULL;

COMMENT ON TABLE agent_discussions IS 'Agent讨论记录，每位Agent对每只股票每轮的完整输出';
```

#### 2.1.2 agent_weights 表 — Agent权重配置与校准

```sql
-- [Schema所有权: DD-04] 权威定义
CREATE TABLE agent_weights (
    id              BIGSERIAL       PRIMARY KEY,
    agent_name      VARCHAR(32)     NOT NULL,               -- Agent名称
    market_state    VARCHAR(16)     NOT NULL,               -- 适用市场状态
    -- 权重 [PRD-T-100]
    base_weight     NUMERIC(4,2)    NOT NULL,               -- 基准权重(市场状态决定)
    calib_factor    NUMERIC(4,2)    NOT NULL DEFAULT 1.0,   -- 校准系数 [PRD-T-106] 上限1.3/下限0.3
    effective_weight NUMERIC(4,2)   NOT NULL,               -- 有效权重 = base_weight × calib_factor
    -- 胜率统计 [PRD-T-104]
    win_rate        NUMERIC(5,4)    DEFAULT 0.5,            -- 最近20次滚动胜率
    recent_count    INTEGER         DEFAULT 0,              -- 统计样本数
    -- 极端评分监控 [PRD-T-099]
    extreme_count   INTEGER         DEFAULT 0,              -- 连续极端评分次数
    is_degraded     BOOLEAN         DEFAULT FALSE,          -- 是否已被降权
    -- 通用字段
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_agent_weight UNIQUE (agent_name, market_state),
    CONSTRAINT chk_calib_factor CHECK (calib_factor >= 0.3 AND calib_factor <= 1.3),  -- PRD L938 强约束
    CONSTRAINT chk_base_weight CHECK (base_weight > 0 AND base_weight <= 1.0)
);

-- 初始数据：主线行情明确的权重配置 [PRD-T-100] PRD L328
INSERT INTO agent_weights (agent_name, market_state, base_weight, calib_factor, effective_weight) VALUES
('mainline_hunter',  'mainline_confirmed', 0.35, 1.0, 0.35),
('fund_detective',   'mainline_confirmed', 0.25, 1.0, 0.25),
('sentiment_catcher','mainline_confirmed', 0.15, 1.0, 0.15),
('experience_judge', 'mainline_confirmed', 0.25, 1.0, 0.25);

-- 初始数据：震荡市/无主线的权重配置 [PRD-T-100] PRD L329
INSERT INTO agent_weights (agent_name, market_state, base_weight, calib_factor, effective_weight) VALUES
('mainline_hunter',  'oscillating', 0.20, 1.0, 0.20),
('fund_detective',   'oscillating', 0.25, 1.0, 0.25),
('sentiment_catcher','oscillating', 0.20, 1.0, 0.20),
('experience_judge', 'oscillating', 0.35, 1.0, 0.35);

COMMENT ON TABLE agent_weights IS 'Agent权重配置与校准，按市场状态分组，含滚动胜率追踪';
```

#### 2.1.3 agent_decisions 表 — 最终加权投票决策

```sql
-- [Schema所有权: DD-04] 权威定义
CREATE TABLE agent_decisions (
    id              BIGSERIAL       PRIMARY KEY,
    date            DATE            NOT NULL,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    -- 加权投票结果
    total_score     NUMERIC(6,2),                           -- 加权总分
    buy_score_sum   NUMERIC(6,2),                           -- 买入理由加权总分 [PRD-T-103]
    against_score_sum NUMERIC(6,2),                         -- 反对理由加权总分
    net_score       NUMERIC(6,2),                           -- buy_score_sum - against_score_sum
    -- 决策结果
    decision        VARCHAR(16)    NOT NULL,                 -- buy/hold/reject
    decision_reason TEXT,                                    -- 决策原因
    -- 各Agent贡献
    agent_votes_json JSONB        NOT NULL DEFAULT '{}',     -- {agent_name: {score, weight, effective_score}}
    -- 风控
    risk_veto       BOOLEAN       DEFAULT FALSE,             -- 风控一票否决 [PRD-T-101]
    risk_veto_reason VARCHAR(128),                           -- 否决原因
    -- 收敛信息
    convergence_rounds SMALLINT   DEFAULT 0,                 -- 实际收敛轮次
    convergence_method VARCHAR(32),                          -- normal/trimmed_mean/degraded
    -- 通用字段
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uk_decision UNIQUE (date, stock_code)
);

CREATE INDEX idx_agent_dec_date ON agent_decisions(date DESC);

COMMENT ON TABLE agent_decisions IS '最终加权投票决策，每日每只标的一条，含风控否决标记';
```

#### 2.1.4 llm_usage 表 — LLM Token 用量监控

```sql
-- [Schema所有权: DD-04] 权威定义 [PRD-T-112] [PRD-T-113]
CREATE TABLE llm_usage (
    id                SERIAL        PRIMARY KEY,
    date              DATE          NOT NULL,
    model             VARCHAR(32)   NOT NULL,                -- LLM模型名
    agent_name        VARCHAR(32),                            -- Agent名称(可为空表示非Agent调用)
    prompt_tokens     INTEGER       DEFAULT 0,               -- [PRD-T-112]
    completion_tokens INTEGER       DEFAULT 0,               -- [PRD-T-112]
    total_cost        DECIMAL(10,4) DEFAULT 0,               -- 估算成本(元)
    call_count        INTEGER       DEFAULT 1,               -- 调用次数
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uk_llm_usage UNIQUE (date, model, agent_name)
);

CREATE INDEX idx_llm_usage_date ON llm_usage(date DESC);
CREATE INDEX idx_llm_usage_model ON llm_usage(model, date DESC);

COMMENT ON TABLE llm_usage IS 'LLM Token用量监控，每日每模型每Agent汇总一条';
```

#### 2.1.5 agent_prompts 表 — Agent提示词版本管理

```sql
-- [Schema所有权: DD-04] 权威定义
CREATE TABLE agent_prompts (
    id              BIGSERIAL       PRIMARY KEY,
    agent_name      VARCHAR(32)     NOT NULL,
    version         VARCHAR(16)     NOT NULL,                -- V1/V2/V3/V4
    system_prompt   TEXT            NOT NULL,                -- 系统提示词
    user_prompt_template TEXT       NOT NULL,                -- 用户提示词模板({{占位符}})
    is_active       BOOLEAN         NOT NULL DEFAULT FALSE,  -- 当前激活版本
    change_note     TEXT,                                    -- 变更说明
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_agent_prompt_version UNIQUE (agent_name, version)
);

CREATE INDEX idx_agent_prompts_active ON agent_prompts(agent_name) WHERE is_active = TRUE;

COMMENT ON TABLE agent_prompts IS 'Agent提示词版本管理，支持迭代式开发(V1→V4)';
```

### 2.2 SQLAlchemy 模型

```python
from sqlalchemy import (
    Column, BigInteger, SmallInteger, Integer, String, Numeric,
    Boolean, Text, Date, DateTime, JSON, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base, TimestampMixin

class AgentDiscussion(Base, TimestampMixin):
    """Agent讨论记录"""
    __tablename__ = "agent_discussions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    round_num = Column(SmallInteger, nullable=False, default=1)
    agent_name = Column(String(32), nullable=False)
    score = Column(SmallInteger)
    buy_reasons = Column(JSONB, nullable=False, default=list)
    against_reasons = Column(JSONB, nullable=False, default=list)
    confidence = Column(Numeric(4, 2), default=0.5)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    model_name = Column(String(32))
    is_valid = Column(Boolean, nullable=False, default=True)
    invalid_reason = Column(String(64))
    predicted_outcome = Column(String(16))
    actual_outcome = Column(String(16))
    outcome_updated_at = Column(DateTime(timezone=True))
    raw_response = Column(Text)


class AgentWeight(Base, TimestampMixin):
    """Agent权重配置与校准"""
    __tablename__ = "agent_weights"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_name = Column(String(32), nullable=False)
    market_state = Column(String(16), nullable=False)
    base_weight = Column(Numeric(4, 2), nullable=False)
    calib_factor = Column(Numeric(4, 2), nullable=False, default=1.0)
    effective_weight = Column(Numeric(4, 2), nullable=False)
    win_rate = Column(Numeric(5, 4), default=0.5)
    recent_count = Column(Integer, default=0)
    extreme_count = Column(Integer, default=0)
    is_degraded = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint("agent_name", "market_state", name="uk_agent_weight"),
        CheckConstraint(
            "calib_factor >= 0.3 AND calib_factor <= 1.3",
            name="chk_calib_factor"
        ),
    )


class AgentDecision(Base, TimestampMixin):
    """最终加权投票决策"""
    __tablename__ = "agent_decisions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    stock_code = Column(String(10), nullable=False)
    total_score = Column(Numeric(6, 2))
    buy_score_sum = Column(Numeric(6, 2))
    against_score_sum = Column(Numeric(6, 2))
    net_score = Column(Numeric(6, 2))
    decision = Column(String(16), nullable=False)
    decision_reason = Column(Text)
    agent_votes_json = Column(JSONB, nullable=False, default=dict)
    risk_veto = Column(Boolean, default=False)
    risk_veto_reason = Column(String(128))
    convergence_rounds = Column(SmallInteger, default=0)
    convergence_method = Column(String(32))
    
    __table_args__ = (
        UniqueConstraint("date", "stock_code", name="uk_decision"),
    )


class LlmUsage(Base):
    """LLM Token用量监控"""
    __tablename__ = "llm_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    model = Column(String(32), nullable=False)
    agent_name = Column(String(32))
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_cost = Column(Numeric(10, 4), default=0)
    call_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("date", "model", "agent_name", name="uk_llm_usage"),
    )


class AgentPrompt(Base, TimestampMixin):
    """Agent提示词版本管理"""
    __tablename__ = "agent_prompts"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_name = Column(String(32), nullable=False)
    version = Column(String(16), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    change_note = Column(Text)
    
    __table_args__ = (
        UniqueConstraint("agent_name", "version", name="uk_agent_prompt_version"),
    )
```

### 2.3 Pydantic 模型 — Agent结构化输出

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
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

# [PRD-T-093] 结构化输出：Pydantic模型
class AgentOutput(BaseModel):
    """单个Agent对单只股票的分析输出"""
    agent_name: AgentName
    score: int = Field(ge=0, le=100, description="评分0-100")
    buy_reasons: list[str] = Field(min_length=1, description="买入理由，至少1条")
    against_reasons: list[str] = Field(min_length=1, description="反对理由，至少1条")  # [PRD-T-102]
    confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="信心度")
    predicted_outcome: PredictedOutcome = Field(default=PredictedOutcome.HOLD)
    supplement: Optional[str] = None

    @field_validator("score")
    @classmethod
    def score_must_be_valid(cls, v: int) -> int:
        if not (0 <= v <= 100):  # [PRD-T-095] 评分不在0-100→无效
            raise ValueError(f"Score {v} out of range [0, 100]")
        return v

class AgentDiscussionRound(BaseModel):
    """一轮讨论结果"""
    round_num: int = Field(ge=1, le=3)
    stock_code: str
    outputs: list[AgentOutput]
    max_score_diff: float = Field(description="本轮最大分差")
    is_converged: bool = Field(description="是否已收敛(分差<=30)")

class WeightedVoteResult(BaseModel):
    """加权投票结果"""
    stock_code: str
    total_score: float
    buy_score_sum: float          # [PRD-T-103]
    against_score_sum: float
    net_score: float
    decision: DecisionType
    risk_veto: bool = False       # [PRD-T-101]
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
```

---

## 3. API 契约

### 3.1 API 端点总览

| 方法 | 端点 | 说明 | 鉴权 |
|:-----|:-----|:-----|:----:|
| GET | `/api/v1/agent/discussions` | 查询讨论记录 | ✅ |
| GET | `/api/v1/agent/discussions/{date}/{stock_code}` | 查询某日某标讨论详情 | ✅ |
| GET | `/api/v1/agent/decisions` | 查询决策记录 | ✅ |
| GET | `/api/v1/agent/decisions/{date}` | 查询某日决策 | ✅ |
| GET | `/api/v1/agent/weights` | 查询当前权重配置 | ✅ |
| PUT | `/api/v1/agent/weights` | 更新基准权重 | ✅ |
| POST | `/api/v1/agent/trigger` | 手动触发Agent分析 | ✅ |
| GET | `/api/v1/agent/calibration` | 查询校准面板数据 | ✅ |
| GET | `/api/v1/agent/llm-usage` | 查询LLM用量统计 | ✅ |
| PUT | `/api/v1/agent/llm-budget` | 设置Token预算 | ✅ |
| GET | `/api/v1/agent/prompts` | 查询提示词列表 | ✅ |
| PUT | `/api/v1/agent/prompts/{id}/activate` | 激活提示词版本 | ✅ |

### 3.2 查询讨论记录

**GET** `/api/v1/agent/discussions`

**请求参数**：

| 参数 | 类型 | 必选 | 说明 |
|:-----|:-----|:----:|:-----|
| date | string(YYYY-MM-DD) | ❌ | 讨论日期，默认今天 |
| stockCode | string | ❌ | 股票代码 |
| agentName | string | ❌ | Agent名称 |
| page | int | ❌ | 页码，默认1 |
| pageSize | int | ❌ | 每页条数，默认20 |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "date": "2026-05-01",
        "stockCode": "002456",
        "roundNum": 1,
        "agentName": "mainline_hunter",
        "score": 85,
        "buyReasons": ["商业航天政策持续落地", "板块资金集中度上升"],
        "againstReasons": ["板块集中度连续2天下降，可能退潮"],
        "confidence": 0.8,
        "isValid": true,
        "predictedOutcome": "buy",
        "actualOutcome": "pending",
        "promptTokens": 1200,
        "completionTokens": 450,
        "modelName": "deepseek-v3",
        "createdAt": "2026-05-01T15:10:30+08:00"
      }
    ],
    "total": 60,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.3 查询决策记录

**GET** `/api/v1/agent/decisions/{date}`

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "date": "2026-05-01",
    "decisions": [
      {
        "stockCode": "002456",
        "totalScore": 78.5,
        "buyScoreSum": 82.0,
        "againstScoreSum": 45.0,
        "netScore": 37.0,
        "decision": "buy",
        "decisionReason": "买入理由加权总分82.0显著高于反对理由加权总分45.0，净分37.0超阈值",
        "riskVeto": false,
        "convergenceRounds": 2,
        "convergenceMethod": "normal",
        "agentVotes": {
          "mainline_hunter": {"score": 85, "weight": 0.35, "effectiveScore": 29.75},
          "fund_detective": {"score": 70, "weight": 0.25, "effectiveScore": 17.5},
          "sentiment_catcher": {"score": 65, "weight": 0.15, "effectiveScore": 9.75},
          "experience_judge": {"score": 80, "weight": 0.25, "effectiveScore": 20.0}
        }
      }
    ]
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.4 查询权重配置

**GET** `/api/v1/agent/weights`

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "weights": [
      {
        "agentName": "mainline_hunter",
        "marketState": "mainline_confirmed",
        "baseWeight": 0.35,
        "calibFactor": 1.1,
        "effectiveWeight": 0.385,
        "winRate": 0.65,
        "recentCount": 20,
        "extremeCount": 0,
        "isDegraded": false
      }
    ],
    "currentMarketState": "mainline_confirmed"
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.5 更新基准权重

**PUT** `/api/v1/agent/weights`

**请求体**：

```json
{
  "weights": [
    {
      "agentName": "mainline_hunter",
      "marketState": "mainline_confirmed",
      "baseWeight": 0.35
    }
  ]
}
```

**约束**：同一 market_state 下4个Agent的 base_weight 总和必须等于1.0。

### 3.6 手动触发Agent分析

**POST** `/api/v1/agent/trigger`

**请求体**：

```json
{
  "stockCodes": ["002456", "600036"],
  "forceRerun": false
}
```

**响应**：

```json
{
  "code": 0,
  "message": "Agent分析任务已提交",
  "data": {
    "taskId": "agent_20260501_001",
    "status": "running",
    "stockCount": 2
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.7 查询校准面板数据

**GET** `/api/v1/agent/calibration`

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "agents": [
      {
        "agentName": "mainline_hunter",
        "displayName": "主线猎手",
        "winRate": 0.65,
        "recentCount": 20,
        "calibFactor": 1.1,
        "history": [
          {"date": "2026-04-30", "predicted": "buy", "actual": "win"},
          {"date": "2026-04-29", "predicted": "buy", "actual": "loss"}
        ],
        "winRateTrend": [0.55, 0.58, 0.62, 0.65]
      }
    ]
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.8 查询LLM用量统计

**GET** `/api/v1/agent/llm-usage`

**请求参数**：

| 参数 | 类型 | 必选 | 说明 |
|:-----|:-----|:----:|:-----|
| startDate | string | ❌ | 开始日期，默认7天前 |
| endDate | string | ❌ | 结束日期，默认今天 |
| groupBy | string | ❌ | day/agent/model，默认day |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "dailyUsage": [
      {
        "date": "2026-05-01",
        "totalPromptTokens": 50000,
        "totalCompletionTokens": 15000,
        "totalCost": 0.85,
        "callCount": 40
      }
    ],
    "budgetStatus": {
      "dailyLimit": 100000,
      "dailyUsed": 65000,
      "monthlyLimit": 2000000,
      "monthlyUsed": 800000,
      "isOverBudget": false,
      "degradeLevel": "none"
    }
  },
  "timestamp": "2026-05-01T15:30:00+08:00"
}
```

### 3.9 错误码定义

| 错误码 | HTTP状态码 | 含义 |
|:-------|:----------|:-----|
| 40301 | 500 | Agent讨论超时（所有Agent超时） |
| 40302 | 422 | Agent输出格式无效 |
| 40303 | 409 | Agent分析任务已在运行中 |
| 40304 | 422 | 权重配置不合法（总和≠1.0） |
| 40305 | 502 | LLM API不可用 |
| 40306 | 429 | Token预算已超限 |
| 40307 | 422 | 提示词激活失败（版本不存在） |
| 40308 | 500 | Agent讨论不收敛（3轮后仍未收敛，已降级为trimmed mean） |
| 40309 | 404 | 讨论记录不存在 |
| 40310 | 500 | TradingAgents框架初始化失败 |

---

## 4. 业务逻辑伪代码

### 4.1 TradingAgents Fork 改造架构

```
# [PRD-T-090] Agent编排 — 选TradingAgents Fork
# [PRD-T-091] Fork TradingAgents → 替换4个Agent提示词 → 接入A股数据源

Fork改造范围：
1. 保留 TradingAgents 核心辩论循环逻辑
2. 替换 Bull/Bear Agent → 四位自定义Agent
   - mainline_hunter (主线猎手) ← 替换 Bull Agent
   - fund_detective (资金侦探) ← 新增
   - sentiment_catcher (情绪捕手) ← 新增
   - experience_judge (经验法官) ← 替换 Bear Agent
3. 替换美股数据源 → A股数据源(DD-02/DD-03)
4. 替换原始输出 → Pydantic结构化输出 [PRD-T-093]
5. 增加输出校验器 AgentOutputValidator [PRD-T-095~T-099]
6. 增加加权投票器 WeightedVoter [PRD-T-100~T-101]
7. 增加权重校准器 WeightCalibrator [PRD-T-104~T-106]
8. 增加Token计数器 TokenCounter [PRD-T-112~T-113]
```

### 4.2 四位Agent定义与输入输出

```
# [PRD-T-109] Agent聚焦定性判断，定量由评分层处理
# [PRD-T-110] 不用Agent算数学、不让Agent读K线

Agent 1: mainline_hunter (主线猎手)
  职责: 判断主线行情的持续性和逻辑硬度
  定性输入(应增加):
    - 近期政策文件原文摘要
    - 行业新闻标题+摘要(最近5条)
    - 板块资金集中度变化趋势(5日描述性文本)
    - 宏观经济周期位置描述
  定量输入(应减少/已由评分层处理):
    - ❌ 均线/成交量/ADX等技术数据
    - ✅ 评分层已算好的"量价维度分"和"逻辑维度分"
  输出: AgentOutput {score, buy_reasons, against_reasons, confidence}

Agent 2: fund_detective (资金侦探)
  职责: 判断资金面是否真实支撑行情
  定性输入(应增加):
    - 近5日主力资金趋势描述
    - 大单/小单比例变化方向
    - 筹码分布变化描述
    - 龙虎榜特征描述
  定量输入(应减少):
    - ❌ 单日资金流向数值
    - ✅ 评分层已算好的"资金维度分"
  输出: AgentOutput {score, buy_reasons, against_reasons, confidence}

Agent 3: sentiment_catcher (情绪捕手)
  职责: 判断市场情绪是否过热或过冷
  定性输入(应增加):
    - 板块涨停家数变化趋势
    - 舆情情绪倾向描述
    - 散户讨论热度描述
    - 新闻情绪标签
  定量输入(应减少):
    - ❌ 涨跌幅百分比
    - ✅ 评分层已算好的"情绪维度分"
  输出: AgentOutput {score, buy_reasons, against_reasons, confidence}

Agent 4: experience_judge (经验法官)
  职责: 从历史经验角度提供证伪视角
  定性输入(应增加):
    - 统计报告(按策略/板块/市场状态)
    - 匹配经验的原因说明(来自DD-07)
    - 类似场景的成败归因
  定量输入(应减少):
    - ❌ 单条经验匹配分数
    - ✅ 经验库匹配的经验条目摘要
  输出: AgentOutput {score, buy_reasons, against_reasons, confidence}
```

### 4.3 Agent 输入数据组装

```pseudocode
# 幂等性：是（同一天同一标的组装结果一致）
function build_agent_input(stock_code: string, date: date) -> dict:
    """
    组装四位Agent的输入数据。
    核心原则：评分层→做数学，Agent层→做判断 [PRD-T-109] [PRD-T-110]
    """

    # ──── 获取评分层结果（来自DD-03 stock_pool）────
    # [Schema: DD-03.stock_pool] 评分结果
    pool_record = [DB] SELECT * FROM stock_pool
                   WHERE stock_code = stock_code AND date = date LIMIT 1

    if pool_record is None then
        [RAISE] Error(40309, "该标的不在股票池中")
    end if

    # ──── 获取市场状态（来自DD-03 market_state_log）────
    # [Schema: DD-03.market_state_log] 市场状态
    market_state = [DB] SELECT to_state FROM market_state_log
                   WHERE date <= date ORDER BY date DESC LIMIT 1

    # ──── 获取板块数据（来自DD-02 sector_data）────
    # [Schema: DD-02.sector_data] 板块数据
    sector_info = [DB] SELECT sector_code, sector_name, change_pct, fund_flow
                  FROM sector_data WHERE date = date ORDER BY fund_flow DESC LIMIT 5

    # ──── 获取新闻数据（来自DD-02 news）────
    # [Schema: DD-02.news] 新闻数据
    news_list = [DB] SELECT title, summary, sentiment_label, published_at
                FROM news WHERE date = date AND stock_code = stock_code
                ORDER BY published_at DESC LIMIT 5

    # ──── 获取资金流向描述（来自DD-02 fund_flows）────
    # [Schema: DD-02.fund_flows] 资金流向
    fund_5d = [DB] SELECT date, main_net_inflow, big_order_pct, small_order_pct
              FROM fund_flows WHERE stock_code = stock_code
              AND date >= date - INTERVAL '5 days' ORDER BY date DESC

    # ──── 获取经验库匹配（来自DD-07 experiences）────
    # [Schema: DD-07.experiences] 经验记录
    exp_matches = [DB] SELECT summary, outcome, strategy_type, similarity
                  FROM experiences WHERE stock_code = stock_code
                  AND outcome IN ('win', 'loss')
                  ORDER BY similarity DESC LIMIT 5

    # ──── 组装各Agent输入 ────
    inputs = {
        "market_state": market_state,
        "score_layer_result": {
            "score_total": pool_record.score_total,
            "score_volume": pool_record.score_volume,     # 量价维度分
            "score_fund": pool_record.score_fund,         # 资金维度分
            "score_sentiment": pool_record.score_sentiment, # 情绪维度分
            "score_mainforce": pool_record.score_mainforce, # 主力维度分
            "score_logic": pool_record.score_logic,       # 逻辑维度分
        },
        "mainline_hunter_input": {
            "sector_trends": format_sector_trends(sector_info),
            "policy_news": filter_policy_news(news_list),  # 政策相关新闻
            "macro_context": get_macro_context(date),      # 宏观经济描述
            "sector_fund_concentration_trend": describe_fund_concentration(fund_5d),
        },
        "fund_detective_input": {
            "fund_trend_5d": describe_fund_trend(fund_5d),     # 5日资金趋势描述
            "big_small_order_direction": describe_order_ratio(fund_5d),
            "chip_distribution": describe_chip_change(stock_code, date),
            "dragon_tiger": get_dragon_tiger_desc(stock_code, date),
        },
        "sentiment_catcher_input": {
            "sector_limit_up_trend": get_limit_up_trend(sector_info, date),
            "news_sentiment": summarize_news_sentiment(news_list),
            "retail_heat": get_retail_heat_desc(stock_code, date),
            "sentiment_label": pool_record.score_sentiment,
        },
        "experience_judge_input": {
            "matched_experiences": format_experiences(exp_matches),
            "strategy_stats": get_strategy_stats(pool_record.strategy_type),
            "market_state_stats": get_market_state_stats(market_state),
        }
    }

    return inputs
end function
```

### 4.4 Agent 讨论主流程

```pseudocode
# 幂等性：否（涉及LLM调用，每次结果可能不同）
# [PRD-T-092] 原生辩论机制
# [PRD-T-094] 多轮讨论2-3轮收敛
# [PRD-T-107] asyncio+aiohttp并发调用LLM，串行禁止

async function run_agent_discussion(
    stock_codes: list[string],
    date: date
) -> list[AgentDecision]:

    # ──── 前置检查 ────
    # 1. Token预算检查 [PRD-T-113]
    budget_ok = check_llm_budget()
    if not budget_ok then
        [LOG] WARNING "Token预算超限，降级为纯规则模式"
        return generate_rule_based_decisions(stock_codes, date)  # [PRD-T-111]
    end if

    # 2. LLM可用性检查
    llm_available = await check_llm_availability()
    if not llm_available then
        [LOG] WARNING "LLM API不可用，降级为纯规则模式"  # [PRD-T-111]
        return generate_rule_based_decisions(stock_codes, date)
    end if

    # ──── 获取市场状态 ────
    # [Schema: DD-03.market_state_log]
    market_state = [DB] SELECT to_state FROM market_state_log
                   WHERE date <= date ORDER BY date DESC LIMIT 1

    # ──── 风控前置检查 [PRD-T-101] ────
    if market_state == "extreme" then
        [LOG] WARNING "极端行情，风控一票否决"
        return [AgentDecision(decision="reject", risk_veto=True,
                risk_veto_reason="极端行情风控否决") for code in stock_codes]
    end if

    # ──── 并发调度所有标的的Agent讨论 [PRD-T-107] ────
    # asyncio.gather 并发调用，不要串行
    tasks = [discuss_single_stock(code, date, market_state) for code in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ──── 处理结果 ────
    decisions = []
    for i, result in enumerate(results):
        if isinstance(result, Exception) then
            [LOG] ERROR f"标的{stock_codes[i]}讨论异常: {result}"
            # 降级：用评分层结果代替
            decisions.append(generate_fallback_decision(stock_codes[i], date))
        else
            decisions.append(result)
        end if
    end for

    # ──── 批量写入数据库 ────
    [DB] BULK INSERT agent_decisions VALUES decisions
    [DB] BULK INSERT agent_discussions VALUES all_discussion_records

    return decisions
end function
```

### 4.5 单只标的讨论流程

```pseudocode
# 幂等性：否（LLM调用+权重读取）
async function discuss_single_stock(
    stock_code: string,
    date: date,
    market_state: string
) -> AgentDecision:

    # ──── 1. 组装Agent输入 ────
    agent_input = build_agent_input(stock_code, date)

    # ──── 2. 读取当前权重 ────
    # [Schema: DD-04.agent_weights]
    weights = [DB] SELECT * FROM agent_weights
              WHERE market_state = market_state

    # ──── 3. 多轮讨论循环 [PRD-T-094] 2-3轮 ────
    all_round_outputs: list[list[AgentOutput]] = []
    is_converged = False
    final_outputs: list[AgentOutput] = []
    convergence_method = "normal"

    for round_num in range(1, 4):  # 最多3轮
        # ──── 3a. 并发调用4个Agent [PRD-T-107] ────
        round_outputs = await call_agents_concurrently(
            stock_code, date, round_num, agent_input, weights
        )

        # ──── 3b. 输出校验 ────
        validated_outputs = validate_agent_outputs(round_outputs)

        # ──── 3c. 保存本轮输出 ────
        all_round_outputs.append(validated_outputs)

        # ──── 3d. 收敛检查 ────
        scores = [o.score for o in validated_outputs if o.is_valid]
        max_diff = max(scores) - min(scores) if len(scores) > 1 else 0

        if max_diff <= 30 then  # 分差<=30，收敛
            is_converged = True
            final_outputs = validated_outputs
            break
        end if

        # ──── 3e. 非收敛：将本轮结果反馈给下一轮 ────
        # Agent可以看到其他Agent的观点后调整评分
        agent_input.previous_round = validated_outputs

        if round_num == 3 then
            # 3轮仍不收敛 [PRD-T-098]
            [LOG] WARNING f"标的{stock_code}讨论3轮不收敛(max_diff={max_diff})"
            final_outputs = validated_outputs
            convergence_method = "trimmed_mean"
        end if
    end for

    # ──── 4. 加权投票 ────
    decision = weighted_vote(
        stock_code, date, market_state, final_outputs, weights, convergence_method
    )

    return decision
end function
```

### 4.6 并发调用4个Agent

```pseudocode
# [PRD-T-107] asyncio+aiohttp并发调用LLM，串行禁止
# [PRD-T-108] 超时60秒跳过该Agent；全部超时降级评分层

async function call_agents_concurrently(
    stock_code: string,
    date: date,
    round_num: int,
    agent_input: dict,
    weights: list[AgentWeight]
) -> list[AgentOutput]:

    agent_names = ["mainline_hunter", "fund_detective",
                   "sentiment_catcher", "experience_judge"]

    # ──── 并发调用4个Agent ────
    async def call_single_agent(agent_name: string) -> AgentOutput:
        try:
            # 获取Agent提示词
            # [Schema: DD-04.agent_prompts]
            prompt_config = [DB] SELECT * FROM agent_prompts
                            WHERE agent_name = agent_name AND is_active = TRUE LIMIT 1

            # 组装完整prompt
            user_prompt = render_prompt_template(
                prompt_config.user_prompt_template,
                agent_input,
                round_num
            )

            # 并发调用LLM，60秒超时 [PRD-T-108]
            result = await asyncio.wait_for(
                call_llm_api(
                    model = prompt_config.model_name,
                    system_prompt = prompt_config.system_prompt,
                    user_prompt = user_prompt,
                    response_format = AgentOutput  # [PRD-T-093] Pydantic结构化输出
                ),
                timeout = 60  # PRD L993 强约束
            )

            # 记录Token用量 [PRD-T-112]
            record_token_usage(
                model = result.model,
                agent_name = agent_name,
                stock_code = stock_code,
                prompt_tokens = result.prompt_tokens,
                completion_tokens = result.completion_tokens
            )

            return result

        except asyncio.TimeoutError:
            # 超时60秒跳过该Agent [PRD-T-108]
            [LOG] WARNING f"Agent {agent_name} 超时(60s)，跳过"
            return AgentOutput(
                agent_name = agent_name,
                score = None,  # 标记为无效
                buy_reasons = [],
                against_reasons = [],
                confidence = 0,
                is_valid = False,
                invalid_reason = "timeout"
            )

        except LLMError as e:
            [LOG] ERROR f"Agent {agent_name} LLM调用失败: {e}"
            return AgentOutput(
                agent_name = agent_name,
                score = None,
                buy_reasons = [],
                against_reasons = [],
                confidence = 0,
                is_valid = False,
                invalid_reason = f"llm_error: {e}"
            )
    end async def

    # 并发执行，不串行 [PRD-T-107]
    results = await asyncio.gather(
        call_single_agent("mainline_hunter"),
        call_single_agent("fund_detective"),
        call_single_agent("sentiment_catcher"),
        call_single_agent("experience_judge")
    )

    # ──── 检查是否全部超时 ────
    valid_count = sum(1 for r in results if r.is_valid)
    if valid_count == 0 then
        # 全部超时/失败 → 降级到评分层 [PRD-T-108]
        [LOG] ERROR "所有Agent超时/失败，降级到评分层"
        [RAISE] Error(40301, "所有Agent超时，降级到评分层")
    end if

    return list(results)
end function
```

### 4.7 Agent 输出校验器

```pseudocode
# [PRD-T-095~T-099] Agent输出校验与不收敛兜底

function validate_agent_outputs(outputs: list[AgentOutput]) -> list[AgentOutput]:
    """
    校验每个Agent的输出，对异常情况进行兜底处理。
    """
    validated = []

    for output in outputs:
        # ──── 校验1: 评分不在0-100 → 无效不参与投票 [PRD-T-095] ────
        if output.score is None or not (0 <= output.score <= 100) then
            output.is_valid = False
            output.invalid_reason = "score_out_of_range"
            [LOG] WARNING f"Agent {output.agent_name} 评分{output.score}不在0-100范围，标记无效"
            validated.append(output)
            continue
        end if

        # ──── 校验2: 反对理由为空 → 评分强制降为50 [PRD-T-096] ────
        if not output.against_reasons or len(output.against_reasons) == 0 then
            original_score = output.score
            output.score = 50  # 证伪机制底线
            output.invalid_reason = None  # 仍有效，但评分被降
            [LOG] WARNING f"Agent {output.agent_name} 反对理由为空，评分从{original_score}强制降为50"
        end if

        # ──── 校验3: 极端评分(0/100) → 权重减半 [PRD-T-097] ────
        if output.score == 0 or output.score == 100 then
            output.is_extreme = True
            [LOG] WARNING f"Agent {output.agent_name} 给出极端评分{output.score}，参与投票时权重减半"
        end if

        # ──── 校验4: 买入理由为空 → 评分也降为50 ────
        if not output.buy_reasons or len(output.buy_reasons) == 0 then
            output.score = 50
            [LOG] WARNING f"Agent {output.agent_name} 买入理由为空，评分降为50"
        end if

        output.is_valid = True
        validated.append(output)
    end for

    # ──── 校验5: 持续极端评分监控 [PRD-T-099] ────
    check_extreme_streak(validated)

    return validated
end function
```

### 4.8 不收敛兜底处理

```pseudocode
# [PRD-T-098] 不收敛(分歧>30)→trimmed mean
# [PRD-T-099] 持续极端(连续5次)→降权50%+告警

function handle_no_convergence(
    scores: list[int],
    outputs: list[AgentOutput]
) -> tuple[float, str]:
    """
    处理讨论不收敛的情况。
    返回: (最终分数, 收敛方法)
    """
    valid_scores = [o.score for o in outputs if o.is_valid]

    if len(valid_scores) < 2 then
        # 有效评分不足2个，直接取均值
        return (mean(valid_scores), "insufficient_data")
    end if

    max_diff = max(valid_scores) - min(valid_scores)

    if max_diff <= 30 then
        # 已收敛
        return (mean(valid_scores), "normal")
    end if

    # 不收敛：丢弃最高分和最低分，取trimmed mean [PRD-T-098]
    sorted_scores = sorted(valid_scores)
    trimmed = sorted_scores[1:-1]  # 去掉最高和最低

    if len(trimmed) == 0 then
        # 只有2个有效评分，无法trimmed，取均值
        trimmed = valid_scores
    end if

    final_score = mean(trimmed)
    [LOG] WARNING f"讨论不收敛(max_diff={max_diff})，采用trimmed mean: {final_score}"

    return (final_score, "trimmed_mean")
end function


function check_extreme_streak(outputs: list[AgentOutput]):
    """
    检查Agent是否持续给出极端评分。
    [PRD-T-099] 连续5次极端评分→降权50%+告警
    """
    for output in outputs:
        if not output.is_valid then
            continue
        end if

        # 查询该Agent最近5次评分
        recent_scores = [DB] SELECT score FROM agent_discussions
                        WHERE agent_name = output.agent_name
                        AND is_valid = TRUE
                        ORDER BY created_at DESC LIMIT 5

        extreme_count = sum(1 for s in recent_scores if s in [0, 100])

        if extreme_count >= 5 then
            # 连续5次极端评分 → 降权50% + 告警 [PRD-T-099]
            [DB] UPDATE agent_weights
                 SET calib_factor = calib_factor * 0.5,
                     is_degraded = TRUE,
                     extreme_count = extreme_count
                 WHERE agent_name = output.agent_name

            [LOG] WARNING f"Agent {output.agent_name} 连续{extreme_count}次极端评分，降权50%"
            [MQ] PUBLISH channel = "agent_alert"
                 message = {"type": "extreme_score_degrade",
                           "agent": output.agent_name,
                           "streak": extreme_count}
        else
            # 更新极端评分计数
            [DB] UPDATE agent_weights
                 SET extreme_count = extreme_count
                 WHERE agent_name = output.agent_name
        end if
    end for
end function
```

### 4.9 加权投票

```pseudocode
# [PRD-T-100] 权重动态分配
# [PRD-T-101] 极端行情：风控一票否决
# [PRD-T-102] 每个Agent必须输出买入理由+反对理由
# [PRD-T-103] 买入理由总分>反对理由总分+阈值才开仓

function weighted_vote(
    stock_code: string,
    date: date,
    market_state: string,
    outputs: list[AgentOutput],
    weights: list[AgentWeight],
    convergence_method: string
) -> AgentDecision:

    # ──── 1. 读取权重配置 ────
    # [PRD-T-100] 根据市场状态选择权重方案
    # 主线行情明确: 主线猎手35%, 资金侦探25%, 情绪捕手15%, 经验法官25%  # PRD L328 软约束
    # 震荡市/无主线: 主线猎手20%, 资金侦探25%, 情绪捕手20%, 经验法官35%  # PRD L329 软约束

    weight_map = {}
    for w in weights:
        if w.market_state == market_state then
            weight_map[w.agent_name] = w.effective_weight
        end if
    end for

    # ──── 2. 计算加权总分 ────
    total_score = 0
    buy_score_sum = 0
    against_score_sum = 0
    agent_votes = {}

    for output in outputs:
        if not output.is_valid then
            continue  # 无效输出不参与投票 [PRD-T-095]
        end if

        agent_weight = weight_map.get(output.agent_name, 0.25)

        # [PRD-T-097] 极端评分权重减半
        if output.is_extreme then
            agent_weight = agent_weight * 0.5
        end if

        effective_score = output.score * agent_weight
        total_score += effective_score

        # [PRD-T-102] [PRD-T-103] 买入理由vs反对理由
        buy_weight = len(output.buy_reasons) * agent_weight
        against_weight = len(output.against_reasons) * agent_weight
        buy_score_sum += output.score * buy_weight / max(buy_weight + against_weight, 0.01)
        against_score_sum += (100 - output.score) * against_weight / max(buy_weight + against_weight, 0.01)

        agent_votes[output.agent_name] = {
            "score": output.score,
            "weight": agent_weight,
            "effective_score": effective_score
        }
    end for

    # ──── 3. 归一化 ────
    weight_sum = sum(agent_votes.values().weight)
    if weight_sum > 0 then
        total_score = total_score / weight_sum * 4  # 归一化到4个Agent
        buy_score_sum = buy_score_sum / weight_sum * 4
        against_score_sum = against_score_sum / weight_sum * 4
    end if

    # ──── 4. 计算净分 ────
    net_score = buy_score_sum - against_score_sum

    # ──── 5. 决策判定 [PRD-T-103] ────
    # 买入理由总分>反对理由总分+阈值才开仓
    threshold = [CONFIG] "agent.decision_threshold"  # 默认10分
    if net_score > threshold then
        decision = "buy"
        decision_reason = f"买入理由加权总分{buy_score_sum:.1f}高于反对理由{against_score_sum:.1f}，净分{net_score:.1f}超阈值{threshold}"
    else if net_score > 0 then
        decision = "hold"
        decision_reason = f"买入理由略高于反对理由，但净分{net_score:.1f}未达阈值{threshold}"
    else
        decision = "reject"
        decision_reason = f"反对理由加权总分{against_score_sum:.1f}高于买入理由{buy_score_sum:.1f}"
    end if

    # ──── 6. 风控否决检查 [PRD-T-101] ────
    risk_veto = False
    risk_veto_reason = None

    # 6a. 极端行情一票否决
    if market_state == "extreme" then
        risk_veto = True
        risk_veto_reason = "极端行情，风控一票否决"
        decision = "reject"
    end if

    # 6b. 查询DD-06风控事件
    # [Schema: DD-06.risk_events] 风控事件
    active_risk = [DB] SELECT * FROM risk_events
                  WHERE date = date AND is_resolved = FALSE LIMIT 1
    if active_risk is not None then
        risk_veto = True
        risk_veto_reason = f"存在未解决风控事件: {active_risk.event_type}"
        decision = "reject"
    end if

    # 6c. 单票流动性检查
    # [Schema: DD-02.fund_flows]
    daily_volume = [DB] SELECT avg_amount FROM fund_flows
                   WHERE stock_code = stock_code AND date = date LIMIT 1
    if daily_volume is not None and daily_volume < [CONFIG] "agent.min_daily_volume" then
        risk_veto = True
        risk_veto_reason = f"日均成交额{daily_volume}低于最低阈值"
        decision = "reject"
    end if

    return AgentDecision(
        stock_code = stock_code,
        total_score = total_score,
        buy_score_sum = buy_score_sum,
        against_score_sum = against_score_sum,
        net_score = net_score,
        decision = decision,
        decision_reason = decision_reason,
        risk_veto = risk_veto,
        risk_veto_reason = risk_veto_reason,
        agent_votes = agent_votes,
        convergence_method = convergence_method
    )
end function
```

### 4.10 权重自动校准

```pseudocode
# [PRD-T-104] 滚动胜率：最近20次推荐统计
# [PRD-T-105] 胜率<40%→降权50%；>70%→提升20%(上限130%)
# [PRD-T-106] 校准系数上限1.3，下限0.3

function calibrate_weights(date: date):
    """
    每日投票前执行权重校准，使用截止到昨日的数据。
    """

    agent_names = ["mainline_hunter", "fund_detective",
                   "sentiment_catcher", "experience_judge"]

    for agent_name in agent_names:
        # ──── 1. 计算滚动胜率 [PRD-T-104] ────
        # 最近20次推荐统计
        recent_records = [DB] SELECT predicted_outcome, actual_outcome
                         FROM agent_discussions
                         WHERE agent_name = agent_name
                         AND predicted_outcome IS NOT NULL
                         AND actual_outcome IN ('win', 'loss')
                         AND date < date
                         ORDER BY date DESC LIMIT 20

        if len(recent_records) == 0 then
            continue  # 无历史数据，保持默认权重
        end if

        win_count = sum(1 for r in recent_records
                       if r.predicted_outcome == "buy" and r.actual_outcome == "win")
        total_count = sum(1 for r in recent_records
                         if r.predicted_outcome == "buy")

        if total_count == 0 then
            win_rate = 0.5  # 无推荐记录，默认0.5
        else
            win_rate = win_count / total_count
        end if

        # ──── 2. 计算校准系数 [PRD-T-105] ────
        # 胜率≥70%→1.3（提升）
        # 60%≤胜率<70%→1.1（微升）
        # 50%≤胜率<60%→1.0（不变）
        # 40%≤胜率<50%→0.7（降低）
        # 胜率<40%→0.5（大幅降低）

        if win_rate >= 0.70 then
            calib_factor = 1.3
        else if win_rate >= 0.60 then
            calib_factor = 1.1
        else if win_rate >= 0.50 then
            calib_factor = 1.0
        else if win_rate >= 0.40 then
            calib_factor = 0.7
        else
            calib_factor = 0.5
        end if

        # ──── 3. 校准系数边界钳位 [PRD-T-106] ────
        calib_factor = max(0.3, min(1.3, calib_factor))  # PRD L938 强约束

        # ──── 4. 更新权重 ────
        market_states = ["mainline_confirmed", "oscillating"]
        for ms in market_states:
            weight_record = [DB] SELECT * FROM agent_weights
                           WHERE agent_name = agent_name AND market_state = ms LIMIT 1

            new_effective = weight_record.base_weight * calib_factor
            # 重新归一化后更新
            [DB] UPDATE agent_weights
                 SET calib_factor = calib_factor,
                     effective_weight = new_effective,
                     win_rate = win_rate,
                     recent_count = total_count
                 WHERE agent_name = agent_name AND market_state = ms
        end for

        [LOG] INFO f"Agent {agent_name} 校准: 胜率={win_rate:.2%}, 校准系数={calib_factor}"
    end for

    # ──── 5. 归一化有效权重 ────
    # 确保同一市场状态下4个Agent的effective_weight总和=1.0
    normalize_weights()
end function


function normalize_weights():
    """归一化同一市场状态下所有Agent的有效权重，使总和=1.0"""
    market_states = ["mainline_confirmed", "oscillating"]

    for ms in market_states:
        all_weights = [DB] SELECT * FROM agent_weights WHERE market_state = ms
        weight_sum = sum(w.effective_weight for w in all_weights)

        if weight_sum > 0 then
            for w in all_weights:
                normalized = w.effective_weight / weight_sum
                [DB] UPDATE agent_weights
                     SET effective_weight = normalized
                     WHERE id = w.id
            end for
        end if
    end for
end function
```

### 4.11 Token 用量监控与预算控制

```pseudocode
# [PRD-T-112] LLM token计数器，每次记录prompt+completion tokens
# [PRD-T-113] 日/月Token预算上限，超限降级

function record_token_usage(
    model: string,
    agent_name: string,
    stock_code: string,
    prompt_tokens: int,
    completion_tokens: int
):
    """
    记录单次LLM调用的Token用量。
    """
    date = today()

    # 估算成本（按模型定价）
    cost = estimate_llm_cost(model, prompt_tokens, completion_tokens)

    # 更新llm_usage表（upsert）
    existing = [DB] SELECT * FROM llm_usage
               WHERE date = date AND model = model AND agent_name = agent_name

    if existing then
        [DB] UPDATE llm_usage
             SET prompt_tokens = prompt_tokens + existing.prompt_tokens,
                 completion_tokens = completion_tokens + existing.completion_tokens,
                 total_cost = total_cost + cost,
                 call_count = call_count + 1
             WHERE id = existing.id
    else
        [DB] INSERT INTO llm_usage (date, model, agent_name,
             prompt_tokens, completion_tokens, total_cost, call_count)
             VALUES (date, model, agent_name,
             prompt_tokens, completion_tokens, cost, 1)
    end if

    # 更新Redis实时计数器
    [REDIS] INCRBY "llm:daily:{date}:prompt_tokens" prompt_tokens
    [REDIS] INCRBY "llm:daily:{date}:completion_tokens" completion_tokens
    [REDIS] INCRBY "llm:monthly:{date:YYYY-MM}:total_tokens" (prompt_tokens + completion_tokens)

    # 检查预算
    check_budget_and_degrade_if_needed()
end function


function check_llm_budget() -> bool:
    """
    检查Token预算是否充足。
    [PRD-T-113] 日/月Token预算上限，超限降级
    """
    date = today()

    # 读取预算配置
    daily_limit = [CONFIG] "llm.budget.daily_tokens"     # 默认100,000
    monthly_limit = [CONFIG] "llm.budget.monthly_tokens" # 默认2,000,000

    # 查询当日用量
    daily_used = [REDIS] GET "llm:daily:{date}:total_tokens" OR 0

    # 查询当月用量
    monthly_used = [REDIS] GET "llm:monthly:{date:YYYY-MM}:total_tokens" OR 0

    if daily_used >= daily_limit then
        [LOG] WARNING f"日Token预算超限: {daily_used}/{daily_limit}"
        return False
    end if

    if monthly_used >= monthly_limit then
        [LOG] WARNING f"月Token预算超限: {monthly_used}/{monthly_limit}"
        return False
    end if

    return True
end function


function check_budget_and_degrade_if_needed():
    """
    Token超限时的降级策略。
    [PRD-T-113] 超限降级：减少Agent讨论轮数或跳过部分标的
    """
    date = today()
    daily_limit = [CONFIG] "llm.budget.daily_tokens"
    daily_used = [REDIS] GET "llm:daily:{date}:total_tokens" OR 0

    usage_ratio = daily_used / daily_limit

    if usage_ratio >= 1.0 then
        # 超限：完全降级为纯规则模式
        [REDIS] SET "llm:degrade_level" "full"
        [LOG] WARNING "Token预算已用完，完全降级为纯规则模式"
    else if usage_ratio >= 0.8 then
        # 接近超限：减少讨论轮数到1轮，跳过部分标的
        [REDIS] SET "llm:degrade_level" "partial"
        [LOG] WARNING "Token预算使用80%+，部分降级(1轮讨论+跳过非核心标的)"
    else if usage_ratio >= 0.6 then
        # 轻度降级：讨论轮数减为2轮
        [REDIS] SET "llm:degrade_level" "light"
        [LOG] INFO "Token预算使用60%+，轻度降级(2轮讨论)"
    else
        [REDIS] SET "llm:degrade_level" "none"
    end if
end function


function estimate_llm_cost(model: string, prompt_tokens: int, completion_tokens: int) -> float:
    """估算LLM调用成本(元)"""
    # 参考价格(2026年5月，元/千token)
    price_table = {
        "deepseek-v3":      {"prompt": 0.001, "completion": 0.002},
        "glm-4-flash":      {"prompt": 0.001, "completion": 0.002},
        "claude-sonnet":     {"prompt": 0.021, "completion": 0.105},
        "gpt-4o":           {"prompt": 0.0175, "completion": 0.07},
    }

    price = price_table.get(model, price_table["deepseek-v3"])
    cost = (prompt_tokens / 1000 * price["prompt"] +
            completion_tokens / 1000 * price["completion"])
    return cost
end function
```

### 4.12 LLM 降级策略

```pseudocode
# [PRD-T-111] Agent可插拔增强组件，LLM故障降级纯规则
# [PRD-T-108] 全部超时降级评分层

function generate_rule_based_decisions(
    stock_codes: list[string],
    date: date
) -> list[AgentDecision]:
    """
    LLM不可用时的纯规则降级模式。
    直接使用DD-03评分层的结果作为决策依据。
    """
    decisions = []

    for code in stock_codes:
        # [Schema: DD-03.stock_pool] 评分结果
        pool = [DB] SELECT * FROM stock_pool
                WHERE stock_code = code AND date = date LIMIT 1

        if pool is None then
            continue
        end if

        # 使用评分层总分直接决策
        if pool.score_total >= [CONFIG] "agent.rule_threshold.buy" then
            decision_type = "buy"
            reason = f"纯规则模式: 评分{pool.score_total}超过买入阈值"
        else if pool.score_total >= [CONFIG] "agent.rule_threshold.hold" then
            decision_type = "hold"
            reason = f"纯规则模式: 评分{pool.score_total}处于观望区间"
        else
            decision_type = "reject"
            reason = f"纯规则模式: 评分{pool.score_total}低于观望阈值"
        end if

        decisions.append(AgentDecision(
            stock_code = code,
            total_score = pool.score_total,
            buy_score_sum = pool.score_total,
            against_score_sum = 0,
            net_score = pool.score_total,
            decision = decision_type,
            decision_reason = reason,
            convergence_method = "degraded_rule",
            risk_veto = False
        ))
    end for

    [LOG] INFO f"纯规则降级模式生成{len(decisions)}条决策"
    return decisions
end function


function generate_fallback_decision(
    stock_code: string,
    date: date
) -> AgentDecision:
    """
    单只标的讨论失败时的降级决策。
    用评分层分值作为替补。
    """
    # [Schema: DD-03.stock_pool]
    pool = [DB] SELECT * FROM stock_pool
            WHERE stock_code = stock_code AND date = date LIMIT 1

    if pool is not None then
        decision = "buy" if pool.score_total >= 70 else "reject"
    else
        decision = "reject"
        pool.score_total = 0
    end if

    return AgentDecision(
        stock_code = stock_code,
        total_score = pool.score_total,
        decision = decision,
        decision_reason = "Agent讨论失败，降级使用评分层结果",
        convergence_method = "degraded_single",
        risk_veto = False
    )
end function
```

### 4.13 实际结果回填与胜率更新

```pseudocode
# 幂等性：否（更新actual_outcome字段）
function update_actual_outcomes(date: date):
    """
    每日收盘后，回填Agent推荐的actual_outcome。
    用于滚动胜率计算。
    """
    # 查询所有pending的推荐记录
    pending = [DB] SELECT * FROM agent_discussions
              WHERE predicted_outcome = "buy"
              AND actual_outcome = "pending"
              AND date <= date - INTERVAL '1 day'  # 至少T+1才能判断

    for record in pending:
        # 获取该标的在推荐后1-5日的涨跌
        # [Schema: DD-02.daily_klines]
        kline = [DB] SELECT close FROM daily_klines
                WHERE stock_code = record.stock_code
                AND date = record.date + INTERVAL '1 day'  # T+1日

        if kline is None then
            continue  # 尚无T+1数据
        end if

        buy_close = [DB] SELECT close FROM daily_klines
                    WHERE stock_code = record.stock_code AND date = record.date
        if buy_close is None then
            continue
        end if

        # 判断胜负：T+1收盘价 > 买入日收盘价
        pnl_pct = (kline.close - buy_close.close) / buy_close.close
        actual = "win" if pnl_pct > 0 else "loss"

        [DB] UPDATE agent_discussions
             SET actual_outcome = actual,
                 outcome_updated_at = NOW()
             WHERE id = record.id
    end for

    # 更新完成后触发权重校准
    calibrate_weights(date)
end function
```

---

## 5. 状态机与转换规则

### 5.1 Agent分析任务状态机

```
                  ┌─────────┐
                  │ PENDING │ ──── 用户触发或定时触发
                  └────┬────┘
                       │
                       ▼
                  ┌─────────┐
           ┌──────│ RUNNING │──────┐
           │      └────┬────┘      │
           │           │           │
     LLM不可用    正常执行     全部Agent超时
           │           │           │
           ▼           ▼           ▼
     ┌──────────┐ ┌─────────┐ ┌────────────┐
     │ DEGRADED │ │VOTING   │ │ DEGRADED   │
     │(纯规则)  │ │(加权投票)│ │(评分层替补)│
     └────┬─────┘ └────┬────┘ └──────┬─────┘
          │             │             │
          └──────┬──────┘─────────────┘
                 │
                 ▼
           ┌──────────┐
           │COMPLETED │ ──── 决策已写入DB
           └──────────┘
                 │
           (异常时)
                 ▼
           ┌──────────┐
           │ FAILED   │ ──── 记录错误日志
           └──────────┘
```

**状态转换表**：

| 当前状态 | 触发条件 | 目标状态 | 动作 |
|:---------|:---------|:---------|:-----|
| PENDING | 定时任务触发/手动触发 | RUNNING | 组装Agent输入数据 |
| RUNNING | LLM API不可用 | DEGRADED(纯规则) | 调用generate_rule_based_decisions |
| RUNNING | 所有Agent返回结果 | VOTING | 进入加权投票 |
| RUNNING | 所有Agent超时(60s) | DEGRADED(评分层) | 调用generate_fallback_decision |
| RUNNING | 部分Agent成功/部分失败 | VOTING | 成功的参与投票，失败的用评分层替补 |
| VOTING | 投票完成+风控通过 | COMPLETED | 写入agent_decisions |
| VOTING | 风控否决 | COMPLETED | decision=reject, risk_veto=True |
| DEGRADED | 降级决策生成完成 | COMPLETED | 写入agent_decisions, 标记convergence_method |
| RUNNING | 不可恢复异常 | FAILED | 记录错误日志+告警 |

### 5.2 Agent讨论收敛状态

```
Round 1 ─────→ Round 2 ─────→ Round 3 ─────→ Trimmed Mean
  │                │                │               │
  ▼                ▼                ▼               ▼
分差>30          分差>30          分差>30        强制收敛
  │                │                │               │
分差<=30         分差<=30         分差<=30
  │                │                │
  ▼                ▼                ▼
CONVERGED       CONVERGED       CONVERGED      FORCE_CONVERGED
(1轮收敛)       (2轮收敛)       (3轮自然收敛)  (3轮强制收敛)
```

**收敛判定规则**：

| 条件 | 判定 | 处理 |
|:-----|:-----|:-----|
| 所有有效评分分差 ≤ 30 | 已收敛 | 取加权均值 |
| 分差 > 30，轮次 < 3 | 未收敛 | 进入下一轮，Agent可见前轮结果 |
| 分差 > 30，轮次 = 3 | 不收敛 | trimmed mean [PRD-T-098] |

### 5.3 LLM 降级等级

```
none ──→ light ──→ partial ──→ full
(正常)  (2轮讨论) (1轮+跳过) (纯规则)

触发条件:
  none:   日用量 < 60%预算
  light:  日用量 >= 60%预算
  partial: 日用量 >= 80%预算
  full:   日用量 >= 100%预算 或 LLM API不可用
```

| 降级等级 | 讨论轮数 | 标的范围 | Agent数 | 模型 |
|:---------|:---------|:---------|:--------|:-----|
| none | 3轮(2-3轮收敛即停) | 股票池全部 | 4个 | 主力模型(DeepSeek V3) |
| light | 2轮 | 股票池全部 | 4个 | 主力模型 |
| partial | 1轮 | 仅评分前5名 | 4个 | 主力模型 |
| full | 0轮(纯规则) | — | 0个 | — |

---

## 6. 异常处理

### 6.1 异常场景与处理策略

| 异常场景 | 处理策略 | PRD追溯 |
|:---------|:---------|:--------|
| LLM API不可用 | 降级为纯规则模式 | [PRD-T-111] |
| 单个Agent超时(60s) | 跳过该Agent，其他Agent投票 | [PRD-T-108] |
| 所有Agent超时 | 降级到评分层排序结果 | [PRD-T-108] |
| Agent输出格式异常 | Pydantic校验失败→标记无效 | [PRD-T-093] |
| 评分不在0-100 | 标记无效，不参与投票 | [PRD-T-095] |
| 反对理由为空 | 评分强制降为50 | [PRD-T-096] |
| 极端评分(0/100) | 保留但投票权重减半 | [PRD-T-097] |
| 3轮不收敛 | trimmed mean强制收敛 | [PRD-T-098] |
| 连续5次极端评分 | 降权50%+告警 | [PRD-T-099] |
| Token日预算超限 | 完全降级纯规则 | [PRD-T-113] |
| Token月预算超限 | 完全降级纯规则 | [PRD-T-113] |
| 极端行情 | 风控一票否决 | [PRD-T-101] |
| 部分Agent失败部分成功 | 成功的投票，失败的评分层替补 | [PRD-T-108] |
| TradingAgents框架初始化失败 | 记录错误+降级纯规则 | — |

### 6.2 错误码速查

| 错误码 | 场景 | 用户提示 |
|:-------|:-----|:---------|
| 40301 | 所有Agent超时 | "Agent分析超时，已降级为纯规则模式" |
| 40302 | Agent输出格式无效 | "Agent输出格式异常，已自动校验处理" |
| 40303 | 分析任务重复触发 | "Agent分析任务已在运行中，请稍后" |
| 40304 | 权重配置不合法 | "权重配置不合法：总和必须等于1.0" |
| 40305 | LLM API不可用 | "AI分析服务暂不可用，已切换为规则模式" |
| 40306 | Token预算超限 | "AI分析预算已用完，已切换为规则模式" |
| 40308 | 讨论不收敛 | "Agent讨论未收敛，已采用修剪均值法" |

### 6.3 重试策略

```
LLM API调用重试:
  - 重试次数: 2次（共3次机会）
  - 重试间隔: 指数退避 1s → 2s → 4s
  - 重试条件: 网络超时/5xx错误/429限流
  - 不重试: 4xx错误(除429)/响应格式错误

Agent分析任务重试:
  - 不自动重试（每日只运行一次，失败降级）
  - 用户可手动触发重跑: POST /api/v1/agent/trigger?forceRerun=true
```

---

## 7. 与其他模块的交互

### 7.1 模块调用关系图

```
┌─────────┐     stock_pool(评分结果)     ┌─────────┐
│  DD-03  │ ─────────────────────────→ │  DD-04  │
│策略引擎  │     market_state_log       │AI-Agent │
└─────────┘                            └────┬────┘
     ↑                                       │
     │              agent_decisions           │
     │         (决策结果→交易执行)            │
     │                                       ↓
┌─────────┐                            ┌─────────┐
│  DD-02  │ ── news/sector_data/ ────→ │  DD-05  │
│数据管理  │    fund_flows/macro        │交易执行  │
└─────────┘                            └─────────┘
     ↑                                       ↑
     │                                       │
┌─────────┐     experiences(匹配)      ┌─────────┐
│  DD-07  │ ─────────────────────────→ │  DD-06  │
│经验库   │                            │风险监控  │
└─────────┘                            └─────────┘
```

### 7.2 关键交互时序

#### 7.2.1 每日收盘后Agent分析时序

```
15:00 收盘
  │
  ├── DD-02: 数据采集完成（K线/资金流/新闻）
  │
  ├── DD-03: 粗筛+评分完成 → stock_pool更新
  │
  ├── DD-04: Agent分析开始
  │     │
  │     ├── (1) calibrate_weights() ──── 校准权重(投票前)
  │     │
  │     ├── (2) check_llm_budget() ──── 检查Token预算
  │     │
  │     ├── (3) 对股票池前5-15只标的:
  │     │     └── discuss_single_stock()
  │     │           ├── build_agent_input() ── 读取DD-02/03/07数据
  │     │           ├── call_agents_concurrently() ── 并发调用4Agent
  │     │           ├── validate_agent_outputs() ── 输出校验
  │     │           ├── (2-3轮讨论循环)
  │     │           └── weighted_vote() ── 加权投票+风控
  │     │
  │     └── (4) 写入 agent_decisions + agent_discussions
  │
  ├── DD-05: 根据agent_decisions执行交易
  │
  └── DD-07: 归档当日Agent分析结果到经验库
```

#### 7.2.2 Agent分析优化策略（减少LLM调用）

```
股票池15只标的 × 4Agent × 2-3轮 = 120-180次LLM调用 → 优化为 20-40次

优化策略:
  ├── 仅分析评分最高的前5只（20次调用/轮）
  ├── 如果前5只≥3只被否决 → 从后10只补充3-5只
  ├── 如果被否决≤2只 → 直接投票
  └── 2轮即收敛则不进第3轮
```

### 7.3 跨模块数据引用清单

| 引用数据 | 来源模块 | 来源表 | 引用方式 | 说明 |
|:---------|:---------|:-------|:---------|:-----|
| 股票池评分 | DD-03 | stock_pool | 只读 | Agent输入+降级决策 |
| 市场状态 | DD-03 | market_state_log | 只读 | 权重动态分配依据 |
| 新闻数据 | DD-02 | news | 只读 | 主线猎手/情绪捕手输入 |
| 板块数据 | DD-02 | sector_data | 只读 | 主线猎手输入 |
| 资金流向 | DD-02 | fund_flows | 只读 | 资金侦探输入 |
| 宏观经济 | DD-02 | macroeconomic | 只读 | 主线猎手输入 |
| 经验匹配 | DD-07 | experiences | 只读 | 经验法官输入 |
| K线数据 | DD-02 | daily_klines | 只读 | 实际结果回填 |
| 风控事件 | DD-06 | risk_events | 只读 | 风控否决检查 |
| 交易执行 | DD-05 | trade_orders | 只读 | 实际成交确认 |

### 7.4 消息通道

| 通道 | 方向 | 用途 | 格式 |
|:-----|:-----|:-----|:-----|
| Redis `agent:analysis:status` | DD-04→前端 | 分析进度通知 | `{"taskId": "...", "status": "running", "progress": 0.5}` |
| Redis `agent:alert` | DD-04→DD-06 | 极端评分/降权告警 | `{"type": "extreme_score_degrade", "agent": "..."}` |
| Redis `llm:degrade_level` | DD-04→全系统 | LLM降级等级变更 | `{"level": "partial", "reason": "budget_80pct"}` |
| Redis `agent:decision:completed` | DD-04→DD-05 | 决策完成通知 | `{"date": "...", "buyCount": 2, "rejectCount": 3}` |

---

## 8. 测试要点

### 8.1 单元测试

| 测试场景 | 预期结果 | 覆盖追溯 |
|:---------|:---------|:---------|
| AgentOutput Pydantic校验：score=150 | 校验失败，抛出ValueError | [PRD-T-095] |
| AgentOutput Pydantic校验：score=50 | 校验通过 | [PRD-T-095] |
| 反对理由为空→评分降为50 | score被强制设为50 | [PRD-T-096] |
| 极端评分(0/100)→权重减半 | is_extreme=True，投票时weight×0.5 | [PRD-T-097] |
| 3轮不收敛→trimmed mean | 去掉最高最低取均值 | [PRD-T-098] |
| 连续5次极端评分→降权50% | calib_factor×0.5，is_degraded=True | [PRD-T-099] |
| 校准系数边界：胜率80%→calib=1.3 | calib_factor=1.3，不超过上限 | [PRD-T-106] |
| 校准系数边界：胜率20%→calib=0.3 | calib_factor=0.3，不低于下限 | [PRD-T-106] |
| 权重归一化：4个Agent权重和=1.0 | effective_weight总和=1.0 | [PRD-T-100] |
| 买入理由>反对理由+阈值→buy | decision="buy" | [PRD-T-103] |
| 买入理由<反对理由→reject | decision="reject" | [PRD-T-103] |
| Token日预算超限→降级 | degrade_level="full" | [PRD-T-113] |

### 8.2 集成测试

| 测试场景 | 预期结果 | Mock |
|:---------|:---------|:-----|
| 完整4Agent讨论流程(2轮收敛) | 生成有效AgentDecision | Mock LLM API |
| LLM API超时(60s) | 跳过超时Agent，其他3个投票 | Mock asyncio.wait_for |
| 全部Agent超时 | 降级到评分层结果 | Mock LLM API全部超时 |
| LLM API不可用 | 降级为纯规则模式 | Mock check_llm_availability |
| 极端行情→风控一票否决 | 所有标的decision="reject" | Mock market_state="extreme" |
| 部分Agent失败+部分成功 | 成功的投票+失败替补 | Mock 部分LLM调用失败 |
| 权重校准(模拟20次历史) | calib_factor根据胜率正确更新 | Mock agent_discussions历史 |
| Token预算80%→部分降级 | 讨论轮数减为1轮 | Mock daily_used=80% |

### 8.3 端到端测试

| 测试场景 | 验证点 |
|:---------|:------|
| 每日收盘后完整流程 | 数据采集→粗筛→评分→Agent讨论→投票→决策→归档 |
| 手动触发Agent分析 | POST /api/v1/agent/trigger → 等待完成 → 查询结果 |
| 前端校准面板 | 展示4个Agent的历史胜率和校准系数 |
| 前端LLM用量看板 | 展示日/月Token用量和预算状态 |
| 降级切换体验 | LLM不可用→自动降级→恢复后自动切回 |

### 8.4 性能测试

| 指标 | 目标 | 说明 |
|:-----|:-----|:-----|
| 单只标的4Agent并发调用 | ≤60s/轮 | 4个Agent并发，60s超时 |
| 5只标的完整讨论 | ≤5分钟 | 5只×4Agent×2轮=40次LLM调用 |
| 15只标的完整讨论 | ≤15分钟 | 含优化策略（先5只+补充） |
| 权重校准 | ≤1秒 | 纯DB查询+计算 |
| Token预算检查 | ≤10ms | Redis实时计数器 |
| 降级决策生成 | ≤500ms | 纯规则计算，无LLM调用 |

---

## 附录 A：四位Agent提示词模板

> 提示词采用迭代式开发（V1→V4），此处为V1初始版本框架。

### A.1 主线猎手 (mainline_hunter)

```
## 你的角色
你是"主线猎手"，一个专注于A股主线行情识别的分析师。你的任务是判断某只股票所在板块
是否处于主线行情中，以及行情的持续性如何。

## 你需要分析的数据
- 评分层已算好的维度分：量价维度分、逻辑维度分
- 近期政策文件摘要和行业新闻
- 板块资金集中度5日变化趋势
- 当前宏观经济周期位置

## 你的分析框架
1. 第一步：判断该股票所属板块是否为当前市场主线
   - 是否有持续的政策催化？
   - 板块资金集中度是否在上升？
2. 第二步：评估主线行情的持续性
   - 催化逻辑是否还在早期？
   - 板块内是否有扩散效应？
3. 第三步：综合判断
   - 该股票在主线中的位置（龙头/跟风/边缘）

## 输出格式（严格遵循）
```json
{
  "score": 0-100,
  "buy_reasons": ["理由1", "理由2"],
  "against_reasons": ["至少1条反对理由"],
  "confidence": 0.0-1.0,
  "predicted_outcome": "buy/hold/avoid",
  "supplement": "补充说明(可选)"
}
```

## 评分参考
- 85分以上：板块是明确主线，该股是龙头，催化仍在早期
- 60-85分：板块有主线特征，但持续性或龙头地位有疑虑
- 60分以下：非主线板块或主线已退潮

## 证伪检查清单
请至少从以下角度提出反对理由：
- 板块集中度是否在下降（可能退潮）
- 催化政策是否已充分price in
- 是否存在替代性板块分流资金
- 龙头股是否出现滞涨信号
```

### A.2 资金侦探 (fund_detective)

```
## 你的角色
你是"资金侦探"，一个专注于资金面分析的A股分析师。你的任务是判断资金流向是否真实
支撑当前行情，是否存在主力出货的迹象。

## 你需要分析的数据
- 评分层已算好的维度分：资金维度分、主力维度分
- 近5日主力资金趋势描述
- 大单/小单比例变化方向
- 筹码分布变化描述
- 龙虎榜特征描述

## 你的分析框架
1. 第一步：判断主力资金方向
   - 主力资金是否持续净流入？
   - 大单占比是在增加还是减少？
2. 第二步：识别资金面风险信号
   - 是否存在"放量滞涨"（主力出货特征）？
   - 小单占比是否异常上升（散户接盘）？
3. 第三步：综合判断
   - 资金面是否支持行情持续？

## 输出格式（严格遵循）
{同主线猎手输出格式}

## 评分参考
- 85分以上：主力资金连续3日以上净流入，大单占比上升，无出货信号
- 60-85分：资金面整体偏正面，但有部分疑虑
- 60分以下：资金面偏负面或存在出货信号

## 证伪检查清单
- 大单占比下降+小单上升（可能在出货）
- 主力资金流向与价格走势背离
- 龙虎榜出现游资接力（短期行为）
- 筹码集中度异常变化
```

### A.3 情绪捕手 (sentiment_catcher)

```
## 你的角色
你是"情绪捕手"，一个专注于市场情绪分析的分析师。你的任务是判断当前市场情绪是否
过热或过冷，以及情绪对行情的影响。

## 你需要分析的数据
- 评分层已算好的维度分：情绪维度分
- 板块涨停家数变化趋势
- 舆情情绪倾向描述
- 散户讨论热度描述
- 新闻情绪标签

## 你的分析框架
1. 第一步：评估市场情绪水平
   - 板块涨停家数是在增加还是减少？
   - 舆情整体偏多还是偏空？
2. 第二步：判断情绪是否极端
   - 散户一致性看多比例是否过高？（可能见顶）
   - 市场是否出现恐慌性抛售？（可能超跌）
3. 第三步：综合判断
   - 情绪面对行情是助力还是阻力？

## 输出格式（严格遵循）
{同主线猎手输出格式}

## 评分参考
- 85分以上：情绪偏乐观但未过热，仍有上升空间
- 60-85分：情绪中性或轻微偏多
- 60分以下：情绪过热（可能见顶）或过冷（恐慌）

## 证伪检查清单
- 散户一致性看多比例>80%（可能见顶信号）
- 板块涨停家数连续3天下降（热度退潮）
- 负面舆情集中出现
- 情绪指标与价格走势出现顶背离
```

### A.4 经验法官 (experience_judge)

```
## 你的角色
你是"经验法官"，一个基于历史经验的分析师。你的任务是从经验库中匹配类似场景，
用历史成败来验证或否定当前决策。

## 你需要分析的数据
- 匹配的历史经验条目（来自经验库）
- 统计报告（按策略/板块/市场状态分类）
- 类似场景的成败归因

## 你的分析框架
1. 第一步：匹配相似历史场景
   - 当前市场状态+板块+策略组合是否在历史中出现过？
   - 类似场景的历史胜率如何？
2. 第二步：识别差异性
   - 当前场景与历史匹配场景有什么关键差异？
   - 这些差异是否会导致不同的结果？
3. 第三步：综合判断
   - 历史经验是支持还是反对当前决策？

## 输出格式（严格遵循）
{同主线猎手输出格式}

## 评分参考
- 85分以上：历史类似场景胜率>70%，且当前无重大差异
- 60-85分：历史有一定参考价值，但需注意差异
- 60分以下：历史类似场景胜率低或存在重大差异

## 证伪检查清单
- 上次类似场景是否失败？
- 当前宏观环境与历史场景有何不同？
- 经验库数据是否足够（冷启动阶段样本不足）
- 是否存在"这次不一样"的根本性变化
```

---

## 附录 B：LLM 调用配置参考

### B.1 模型选型策略

| 场景 | 推荐模型 | 原因 | 预估成本 |
|:-----|:---------|:-----|:---------|
| 每日Agent分析 | **DeepSeek V3 / GLM-4 Flash** | 成本低、中文好、推理快 | ~100万token/月 ≈ 10-20元 |
| 关键决策复核 | **Claude Sonnet / GPT-4o** | 判断准确性要求高 | 用量极少，可忽略 |
| 提示词调试 | **DeepSeek V3** | 低成本快速迭代 | 调试成本可忽略 |

### B.2 API 调用参数

```python
LLM_CONFIG = {
    "deepseek-v3": {
        "base_url": "https://api.deepseek.com/v1",
        "max_tokens": 2048,
        "temperature": 0.3,       # 偏低，保持判断稳定性
        "top_p": 0.9,
        "timeout": 60,            # [PRD-T-108]
        "retry": {"max_attempts": 2, "backoff": [1, 2, 4]},
    },
    "glm-4-flash": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "max_tokens": 2048,
        "temperature": 0.3,
        "top_p": 0.9,
        "timeout": 60,
        "retry": {"max_attempts": 2, "backoff": [1, 2, 4]},
    },
    "claude-sonnet": {
        "base_url": "https://api.anthropic.com/v1",
        "max_tokens": 2048,
        "temperature": 0.3,
        "timeout": 60,
        "retry": {"max_attempts": 2, "backoff": [1, 2, 4]},
    },
}
```

### B.3 预算默认值

```python
LLM_BUDGET_DEFAULTS = {
    "daily_tokens": 100000,       # 日预算：10万token
    "monthly_tokens": 2000000,    # 月预算：200万token
    "degrade_thresholds": {
        "light": 0.6,             # 60%日预算→轻度降级
        "partial": 0.8,           # 80%日预算→部分降级
        "full": 1.0,              # 100%日预算→完全降级
    }
}
```

---

> 本文档为DD-04 AI-Agent模块详细设计，覆盖TRACE-MATRIX中T-090至T-113共24项追溯要求。
> 编写完成后需更新TRACE-MATRIX.md中对应行的覆盖状态为✅。
