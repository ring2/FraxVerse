"""
FraxVerse · LLM 客户端与四位 Agent 提示词

严格按 DD-04-AI-Agent模块.md 第4.2~4.6节实现。

核心约束：
- [PRD-T-107] asyncio 并发调用 LLM，串行禁止
- [PRD-T-108] 超时 60 秒跳过该 Agent；全部超时降级评分层
- [PRD-T-109] Agent 聚焦定性判断，定量由评分层处理
- [PRD-T-110] 不用 Agent 算数学、不让 Agent 读 K 线
- [PRD-T-112] LLM token 计数器，每次记录 prompt+completion tokens
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.agent.models import AgentName, AgentOutput, PredictedOutcome

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 4.2 四位 Agent 提示词（附录 A V1 模板）
# ─────────────────────────────────────────────

AGENT_PROMPTS: dict[str, dict[str, str]] = {
    "mainline_hunter": {
        "system": (
            "## 你的角色\n"
            "你是「主线猎手」，一个专注于A股主线行情识别的分析师。你的任务是判断某只股票所在板块"
            "是否处于主线行情中，以及行情的持续性如何。\n\n"
            "## 你的分析框架\n"
            "1. 第一步：判断该股票所属板块是否为当前市场主线\n"
            "   - 是否有持续的政策催化？\n"
            "   - 板块资金集中度是否在上升？\n"
            "2. 第二步：评估主线行情的持续性\n"
            "   - 主线逻辑是否够硬（政策导向 vs 概念炒作）？\n"
            "   - 是否有新的催化因素即将到来？\n\n"
            "## 你必须输出的内容\n"
            "- score: 0-100 整数评分\n"
            "- buy_reasons: 至少1条买入理由\n"
            "- against_reasons: 至少1条反对理由（证伪视角）\n"
            "- confidence: 0-1 信心度\n"
            "- suggested_entry_low / suggested_entry_high: 建议买入价格区间（可选）\n"
            "- strategy_advice: 策略建议（可选，如突破确认后买入或分批建仓）\n\n"
            "## 重要约束\n"
            "- ⚠️ 你只能做定性判断，不要计算任何数学指标\n"
            "- ⚠️ 不要分析K线、均线、成交量\n"
            "- ⚠️ 评分层的量价维度分已经帮你算好了\n"
        ),
        "user_template": (
            "## 当前分析标的\n"
            "股票: {stock_code}\n"
            "日期: {date}\n\n"
            "## 评分层结果\n"
            "- 综合评分: {score_total}\n"
            "- 量价维度分: {score_volume}\n"
            "- 逻辑维度分: {score_logic}\n\n"
            "## 板块趋势\n"
            "{sector_trends}\n\n"
            "## 政策/行业新闻\n"
            "{policy_news}\n\n"
            "## 板块资金集中度变化\n"
            "{fund_concentration}\n\n"
            "## 当前市场状态\n"
            "{market_state}\n\n"
            "{round_context}"
        ),
    },
    "fund_detective": {
        "system": (
            "## 你的角色\n"
            "你是「资金侦探」，一个专注于A股资金面分析的分析师。你的任务是判断某只股票的资金面"
            "是否真实支撑当前行情。\n\n"
            "## 你的分析框架\n"
            "1. 第一步：判断资金面是否支持上涨\n"
            "   - 主力资金趋势是流入还是流出？\n"
            "   - 大单/小单比例变化方向如何？\n"
            "2. 第二步：评估资金面的可持续性\n"
            "   - 筹码分布是否在向优质持有者集中？\n"
            "   - 龙虎榜是否有机构参与？\n\n"
            "## 你必须输出的内容\n"
            "- score: 0-100 整数评分\n"
            "- buy_reasons: 至少1条买入理由\n"
            "- against_reasons: 至少1条反对理由（证伪视角）\n"
            "- confidence: 0-1 信心度\n"
            "- suggested_entry_low / suggested_entry_high: 建议买入价格区间（可选）\n"
            "- strategy_advice: 策略建议（可选，如突破确认后买入或分批建仓）\n\n"
            "## 重要约束\n"
            "- ⚠️ 你只能做定性判断，不要计算任何数学指标\n"
            "- ⚠️ 不要分析K线、均线\n"
            "- ⚠️ 评分层的资金维度分已经帮你算好了\n"
        ),
        "user_template": (
            "## 当前分析标的\n"
            "股票: {stock_code}\n"
            "日期: {date}\n\n"
            "## 评分层结果\n"
            "- 综合评分: {score_total}\n"
            "- 资金维度分: {score_fund}\n"
            "- 主力维度分: {score_mainforce}\n\n"
            "## 5日资金趋势\n"
            "{fund_trend_5d}\n\n"
            "## 大单/小单比例变化\n"
            "{order_ratio_direction}\n\n"
            "## 筹码分布变化\n"
            "{chip_distribution}\n\n"
            "## 龙虎榜特征\n"
            "{dragon_tiger}\n\n"
            "## 当前市场状态\n"
            "{market_state}\n\n"
            "{round_context}"
        ),
    },
    "sentiment_catcher": {
        "system": (
            "## 你的角色\n"
            "你是「情绪捕手」，一个专注于A股市场情绪判断的分析师。你的任务是判断当前市场情绪"
            "是否过热或过冷。\n\n"
            "## 你的分析框架\n"
            "1. 第一步：判断市场情绪处于什么位置\n"
            "   - 板块涨停家数在增加还是减少？\n"
            "   - 舆情情绪倾向如何？\n"
            "2. 第二步：评估情绪的极端程度\n"
            "   - 散户讨论热度是否异常？\n"
            "   - 新闻情绪是否一边倒？\n\n"
            "## 你必须输出的内容\n"
            "- score: 0-100 整数评分\n"
            "- buy_reasons: 至少1条买入理由\n"
            "- against_reasons: 至少1条反对理由（证伪视角）\n"
            "- confidence: 0-1 信心度\n"
            "- suggested_entry_low / suggested_entry_high: 建议买入价格区间（可选）\n"
            "- strategy_advice: 策略建议（可选，如突破确认后买入或分批建仓）\n\n"
            "## 重要约束\n"
            "- ⚠️ 你只能做定性判断，不要计算任何数学指标\n"
            "- ⚠️ 不要分析K线、均线、涨跌幅百分比\n"
            "- ⚠️ 评分层的情绪维度分已经帮你算好了\n"
        ),
        "user_template": (
            "## 当前分析标的\n"
            "股票: {stock_code}\n"
            "日期: {date}\n\n"
            "## 评分层结果\n"
            "- 综合评分: {score_total}\n"
            "- 情绪维度分: {score_sentiment}\n\n"
            "## 板块涨停家数变化趋势\n"
            "{limit_up_trend}\n\n"
            "## 舆情情绪倾向\n"
            "{news_sentiment}\n\n"
            "## 散户讨论热度\n"
            "{retail_heat}\n\n"
            "## 当前市场状态\n"
            "{market_state}\n\n"
            "{round_context}"
        ),
    },
    "experience_judge": {
        "system": (
            "## 你的角色\n"
            "你是「经验法官」，一个基于历史经验和数据做证伪判断的分析师。你的任务是站在历史经验"
            "角度对当前交易机会进行证伪。\n\n"
            "## 你的分析框架\n"
            "1. 第一步：检查历史相似场景\n"
            "   - 类似的市场状态下该策略表现如何？\n"
            "   - 类似的板块/标的历史走势如何？\n"
            "2. 第二步：证伪视角\n"
            "   - 什么情况下这笔交易会失败？\n"
            "   - 历史类似的失败案例有什么共同特点？\n\n"
            "## 你必须输出的内容\n"
            "- score: 0-100 整数评分（越低越反对）\n"
            "- buy_reasons: 至少1条买入理由\n"
            "- against_reasons: 至少1条反对理由（证伪视角）\n"
            "- confidence: 0-1 信心度\n"
            "- suggested_entry_low / suggested_entry_high: 建议买入价格区间（可选）\n"
            "- strategy_advice: 策略建议（可选）\n\n"
            "## 重要约束\n"
            "- ⚠️ 你只能做定性判断，不要计算任何数学指标\n"
            "- ⚠️ 不要分析K线、均线\n"
            "- ⚠️ 你的主要职责是证伪，至少列出1条强的反对理由\n"
        ),
        "user_template": (
            "## 当前分析标的\n"
            "股票: {stock_code}\n"
            "日期: {date}\n\n"
            "## 评分层结果\n"
            "- 综合评分: {score_total}\n\n"
            "## 历史匹配经验\n"
            "{matched_experiences}\n\n"
            "## 该策略历史统计\n"
            "{strategy_stats}\n\n"
            "## 该市场状态历史统计\n"
            "{market_state_stats}\n\n"
            "## 当前市场状态\n"
            "{market_state}\n\n"
            "{round_context}"
        ),
    },
}

# ─────────────────────────────────────────────
# 4.3 Agent 输入数据组装
# ─────────────────────────────────────────────

DEFAULT_DATA_PLACEHOLDERS = {
    "sector_trends": "（暂无板块数据）",
    "policy_news": "（暂无新闻数据）",
    "fund_concentration": "（暂无资金集中度数据）",
    "fund_trend_5d": "（暂无5日资金趋势）",
    "order_ratio_direction": "（暂无订单比例数据）",
    "chip_distribution": "（暂无筹码分布数据）",
    "dragon_tiger": "（暂无龙虎榜数据）",
    "limit_up_trend": "（暂无涨停趋势数据）",
    "news_sentiment": "（暂无舆情数据）",
    "retail_heat": "（暂无散户情绪数据）",
    "matched_experiences": "（暂无匹配经验）",
    "strategy_stats": "（暂无策略统计数据）",
    "market_state_stats": "（暂无市场状态统计）",
    "score_volume": "N/A",
    "score_fund": "N/A",
    "score_sentiment": "N/A",
    "score_mainforce": "N/A",
    "score_logic": "N/A",
}


def build_agent_input(stock_code: str, date: str, score_layer: dict | None = None) -> dict[str, Any]:
    """
    组装四位Agent的输入数据（DD-04 第4.3节）。

    核心原则：评分层→做数学，Agent层→做判断 [PRD-T-109] [PRD-T-110]

    当前实现：使用默认占位符，实际数据待对接 DB 后替换。
    幂等性：是（同一天同一标的组装结果一致）。
    """
    if score_layer is None:
        score_layer = {
            "score_total": 0,
            "score_volume": 0,
            "score_fund": 0,
            "score_sentiment": 0,
            "score_mainforce": 0,
            "score_logic": 0,
        }

    return {
        "market_state": "mainline_confirmed",  # TODO: 从 market_state_log 读取
        "score_layer_result": {
            "score_total": score_layer.get("score_total", 0),
            "score_volume": score_layer.get("score_volume", 0),
            "score_fund": score_layer.get("score_fund", 0),
            "score_sentiment": score_layer.get("score_sentiment", 0),
            "score_mainforce": score_layer.get("score_mainforce", 0),
            "score_logic": score_layer.get("score_logic", 0),
        },
        "mainline_hunter_input": {
            "sector_trends": score_layer.get("sector_trends", DEFAULT_DATA_PLACEHOLDERS["sector_trends"]),
            "policy_news": score_layer.get("policy_news", DEFAULT_DATA_PLACEHOLDERS["policy_news"]),
            "fund_concentration": score_layer.get("fund_concentration", DEFAULT_DATA_PLACEHOLDERS["fund_concentration"]),
            "macro_context": score_layer.get("macro_context", "（暂无宏观经济数据）"),
        },
        "fund_detective_input": {
            "fund_trend_5d": score_layer.get("fund_trend_5d", DEFAULT_DATA_PLACEHOLDERS["fund_trend_5d"]),
            "order_ratio_direction": score_layer.get("order_ratio_direction", DEFAULT_DATA_PLACEHOLDERS["order_ratio_direction"]),
            "chip_distribution": score_layer.get("chip_distribution", DEFAULT_DATA_PLACEHOLDERS["chip_distribution"]),
            "dragon_tiger": score_layer.get("dragon_tiger", DEFAULT_DATA_PLACEHOLDERS["dragon_tiger"]),
        },
        "sentiment_catcher_input": {
            "limit_up_trend": score_layer.get("limit_up_trend", DEFAULT_DATA_PLACEHOLDERS["limit_up_trend"]),
            "news_sentiment": score_layer.get("news_sentiment", DEFAULT_DATA_PLACEHOLDERS["news_sentiment"]),
            "retail_heat": score_layer.get("retail_heat", DEFAULT_DATA_PLACEHOLDERS["retail_heat"]),
        },
        "experience_judge_input": {
            "matched_experiences": score_layer.get("matched_experiences", DEFAULT_DATA_PLACEHOLDERS["matched_experiences"]),
            "strategy_stats": score_layer.get("strategy_stats", DEFAULT_DATA_PLACEHOLDERS["strategy_stats"]),
            "market_state_stats": score_layer.get("market_state_stats", DEFAULT_DATA_PLACEHOLDERS["market_state_stats"]),
        },
    }


def render_prompt_template(
    agent_name: str,
    agent_input: dict[str, Any],
    stock_code: str,
    date: str,
    round_num: int,
    previous_outputs: list[AgentOutput] | None = None,
) -> tuple[str, str]:
    """
    为指定 Agent 渲染 system_prompt + user_prompt。

    返回: (system_prompt, user_prompt)
    """
    prompt_def = AGENT_PROMPTS.get(agent_name)
    if prompt_def is None:
        raise ValueError(f"Unknown agent: {agent_name}")

    score = agent_input.get("score_layer_result", {})
    agent_specific = agent_input.get(f"{agent_name}_input", {})

    # 生成轮次上下文
    round_context = ""
    if round_num > 1 and previous_outputs:
        context_parts = ["## 前一轮讨论结果\n"]
        for prev in previous_outputs:
            if prev.agent_name.value == agent_name:
                continue  # 不把自己的观点反馈给自己
            context_parts.append(
                f"- {prev.agent_name.value}: 评分={prev.score}, "
                f"信心度={prev.confidence}, \n"
                f"  买入理由: {', '.join(prev.buy_reasons[:2])}\n"
                f"  反对理由: {', '.join(prev.against_reasons[:2])}"
            )
        if len(context_parts) > 1:
            round_context = "\n".join(context_parts)

    round_context_str = ""
    if round_context:
        round_context_str = f"## 这是第{round_num}轮讨论\n{round_context}\n\n请根据其他Agent的观点，重新审视你的分析并调整评分。"

    format_map = {
        "stock_code": stock_code,
        "date": date,
        "market_state": agent_input.get("market_state", "unknown"),
        "score_total": score.get("score_total", 0),
        "score_volume": score.get("score_volume", "N/A"),
        "score_fund": score.get("score_fund", "N/A"),
        "score_sentiment": score.get("score_sentiment", "N/A"),
        "score_mainforce": score.get("score_mainforce", "N/A"),
        "score_logic": score.get("score_logic", "N/A"),
        # mainline_hunter
        "sector_trends": agent_specific.get("sector_trends", DEFAULT_DATA_PLACEHOLDERS["sector_trends"]),
        "policy_news": agent_specific.get("policy_news", DEFAULT_DATA_PLACEHOLDERS["policy_news"]),
        "fund_concentration": agent_specific.get("fund_concentration", DEFAULT_DATA_PLACEHOLDERS["fund_concentration"]),
        # fund_detective
        "fund_trend_5d": agent_specific.get("fund_trend_5d", DEFAULT_DATA_PLACEHOLDERS["fund_trend_5d"]),
        "order_ratio_direction": agent_specific.get("order_ratio_direction", DEFAULT_DATA_PLACEHOLDERS["order_ratio_direction"]),
        "chip_distribution": agent_specific.get("chip_distribution", DEFAULT_DATA_PLACEHOLDERS["chip_distribution"]),
        "dragon_tiger": agent_specific.get("dragon_tiger", DEFAULT_DATA_PLACEHOLDERS["dragon_tiger"]),
        # sentiment_catcher
        "limit_up_trend": agent_specific.get("limit_up_trend", DEFAULT_DATA_PLACEHOLDERS["limit_up_trend"]),
        "news_sentiment": agent_specific.get("news_sentiment", DEFAULT_DATA_PLACEHOLDERS["news_sentiment"]),
        "retail_heat": agent_specific.get("retail_heat", DEFAULT_DATA_PLACEHOLDERS["retail_heat"]),
        # experience_judge
        "matched_experiences": agent_specific.get("matched_experiences", DEFAULT_DATA_PLACEHOLDERS["matched_experiences"]),
        "strategy_stats": agent_specific.get("strategy_stats", DEFAULT_DATA_PLACEHOLDERS["strategy_stats"]),
        "market_state_stats": agent_specific.get("market_state_stats", DEFAULT_DATA_PLACEHOLDERS["market_state_stats"]),
        "round_context": round_context_str,
    }

    try:
        user_prompt = prompt_def["user_template"].format(**format_map)
    except KeyError as e:
        logger.warning("Prompt template missing key: %s", e)
        user_prompt = prompt_def["user_template"]

    return prompt_def["system"], user_prompt


# ─────────────────────────────────────────────
# LLM API 调用
# ─────────────────────────────────────────────

@dataclass
class LLMResponse:
    """LLM 调用响应"""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


# LLM 价格表（元/千token）
LLM_PRICE_TABLE: dict[str, dict[str, float]] = {
    "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
    "deepseek-v3": {"prompt": 0.001, "completion": 0.002},
    "deepseek-v4-flash": {"prompt": 0.001, "completion": 0.002},
    "glm-4-flash": {"prompt": 0.001, "completion": 0.002},
    "claude-sonnet": {"prompt": 0.021, "completion": 0.105},
    "gpt-4o": {"prompt": 0.0175, "completion": 0.07},
}

DEFAULT_MODEL = "deepseek-v4-flash"

# 系统提示词：要求 LLM 输出结构化 JSON
STRUCTURED_OUTPUT_SYSTEM = (
    "你是一个A股量化交易Agent。你必须严格按照提供的JSON格式输出分析结果。\n"
    "输出格式：\n"
    '{\n'
    '  "score": <0-100整数>,\n'
    '  "buy_reasons": ["理由1", "理由2", ...],\n'
    '  "against_reasons": ["反对理由1", "反对理由2", ...],\n'
    '  "confidence": <0.0-1.0小数>,\n'
    '  "predicted_outcome": "buy" 或 "hold" 或 "avoid",\n'
    '  "suggested_entry_low": <建议买入价格下限，浮点数，可选>,\n'
    '  "suggested_entry_high": <建议买入价格上限，浮点数，可选>,\n'
    '  "strategy_advice": "策略建议文本（如分批建仓/突破确认后买入），可选"\n'
    '}\n\n'
    "约束：\n"
    "- score 必须在 0-100 之间\n"
    "- buy_reasons 至少1条\n"
    "- against_reasons 至少1条\n"
    "- confidence 表示你对自己判断的信心程度\n"
    "- 如果你有明确的买入价格区间建议，填写 suggested_entry_low 和 suggested_entry_high\n"
    "- strategy_advice 是你的策略建议，如\"分批建仓3笔\"\"突破20日均线确认后买入\"等"
)


def estimate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """估算LLM调用成本（元） [PRD-T-112]"""
    price = LLM_PRICE_TABLE.get(model, LLM_PRICE_TABLE[DEFAULT_MODEL])
    return (prompt_tokens / 1000 * price["prompt"]) + (completion_tokens / 1000 * price["completion"])


def parse_llm_json_response(raw: str) -> dict[str, Any]:
    """
    解析 LLM 返回的 JSON 字符串。

    处理常见格式问题：
    - 被 ```json ... ``` 包裹
    - 多余的中文/说明文字前缀
    - 末尾有多余内容
    """
    text = raw.strip()

    # 尝试提取 ```json ... ``` 内的内容
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.rindex("```") if "```" in text[start:] else len(text)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.rindex("```") if "```" in text[start + 1:] else len(text)
        text = text[start:end].strip()

    # 尝试找到第一个 { 和最后一个 }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        text = text[brace_start : brace_end + 1]

    return json.loads(text)


def _get_db() -> Any:
    """获取数据库 Session（延迟导入避免循环依赖）"""
    from src.db.session import session_local
    return session_local()


def call_llm_api(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
    max_retries: int = 2,
    api_key_override: str | None = None,
    provider_override: str | None = None,
    base_url_override: str | None = None,
    db: Any = None,
    usage_key: str | None = None,
) -> LLMResponse:
    """
    调用 LLM API（同步）。

    从 DB 连接表 + 用途配置中读取厂商、模型、API Key、Base URL。
    支持通过参数覆盖（用于测试或特殊场景）。

    配置解析优先级：
    1. 显式参数（api_key_override / provider_override / base_url_override）
    2. usage_key 指定用途（如 'daily_analysis'），从 DB 读取
    3. 默认值（deepseek / deepseek-chat）

    重试策略（DD-04 第6.3节）：
    - 重试次数: 2次（共3次机会）
    - 重试间隔: 指数退避 1s → 2s → 4s
    - 重试条件: 网络超时/5xx错误/429限流
    - 不重试: 4xx错误(除429)/响应格式错误
    """
    # 如果有显式覆盖参数，优先使用
    if api_key_override and provider_override:
        pass  # 直接走下面的调用
    elif usage_key:
        # 从 DB 读取用途配置
        close_db = False
        if db is None:
            db = _get_db()
            close_db = True
        try:
            from src.agent.llm_providers import resolve_llm_config
            resolved = resolve_llm_config(db, usage_key=usage_key)
            api_key_override = resolved["api_key"]
            provider_override = resolved["provider_name"]
            base_url_override = base_url_override or resolved["base_url"]
            model = model or resolved["model"]
        finally:
            if close_db:
                db.close()

    # 最终确定参数
    actual_api_key = api_key_override or ""
    actual_provider = provider_override or "deepseek"
    actual_base_url = base_url_override or None

    if not actual_api_key:
        logger.warning("API Key not configured, using mock LLM")
        return _mock_llm_call(system_prompt, user_prompt)

    try:
        from src.agent.llm_providers import call_llm_with_provider
        content, used_model, usage = call_llm_with_provider(
            provider_name=actual_provider,
            api_key=actual_api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            base_url_override=actual_base_url,
            max_retries=max_retries,
        )
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"LLM API call failed: {e}") from e

    return LLMResponse(
        content=content,
        model=used_model,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        latency_ms=0,  # 内部已计时
    )


def _mock_llm_call(system_prompt: str, user_prompt: str) -> LLMResponse:
    """Mock LLM 调用（开发/无 API Key 时使用）"""
    import random

    # 根据提示词中的 Agent 名称生成合理的模拟响应
    score = random.randint(30, 95)
    confidence = round(random.uniform(0.3, 0.9), 2)
    predicted = random.choice(["buy", "hold", "avoid"])

    mock_data = {
        "score": score,
        "buy_reasons": ["板块资金持续流入", "政策面有催化预期"],
        "against_reasons": ["短期涨幅已较大", "大盘环境偏弱"],
        "confidence": confidence,
        "predicted_outcome": predicted,
    }

    return LLMResponse(
        content=json.dumps(mock_data, ensure_ascii=False),
        model="mock-llm",
        prompt_tokens=len(system_prompt.split()) + len(user_prompt.split()),
        completion_tokens=100,
        latency_ms=random.randint(200, 3000),
    )


def call_single_agent(
    agent_name: str,
    stock_code: str,
    date: str,
    agent_input: dict[str, Any],
    round_num: int,
    previous_outputs: list[AgentOutput] | None = None,
    timeout: int = 60,
) -> AgentOutput:
    """
    调用单个 Agent 的 LLM 并解析为结构化输出。

    对应 DD-04 第4.6节 call_single_agent 伪代码。
    [PRD-T-108] 超时60秒跳过该Agent。
    """
    system_prompt, user_prompt = render_prompt_template(
        agent_name=agent_name,
        agent_input=agent_input,
        stock_code=stock_code,
        date=date,
        round_num=round_num,
        previous_outputs=previous_outputs,
    )

    # 组合完整 system prompt（结构化输出要求 + Agent 角色定义）
    full_system = STRUCTURED_OUTPUT_SYSTEM + "\n\n---\n\n" + system_prompt

    try:
        llm_resp = call_llm_api(
            system_prompt=full_system,
            user_prompt=user_prompt,
            timeout=timeout,
        )
    except Exception as e:
        logger.error("Agent %s LLM call failed: %s", agent_name, e)
        return AgentOutput(
            agent_name=AgentName(agent_name),
            score=0,
            buy_reasons=[],
            against_reasons=[],
            confidence=0.0,
            predicted_outcome=PredictedOutcome.AVOID,
            supplement=f"llm_error: {e}",
        )

    # 解析 JSON 响应
    try:
        data = parse_llm_json_response(llm_resp.content)
        return AgentOutput(
            agent_name=AgentName(agent_name),
            score=data["score"],
            buy_reasons=data["buy_reasons"],
            against_reasons=data["against_reasons"],
            confidence=float(data.get("confidence", 0.5)),
            predicted_outcome=PredictedOutcome(data.get("predicted_outcome", "hold")),
            suggested_entry_low=data.get("suggested_entry_low"),
            suggested_entry_high=data.get("suggested_entry_high"),
            strategy_advice=data.get("strategy_advice"),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Agent %s JSON parse error: %s | raw: %s", agent_name, e, llm_resp.content[:200])
        return AgentOutput(
            agent_name=AgentName(agent_name),
            score=0,
            buy_reasons=[],
            against_reasons=[],
            confidence=0.0,
            predicted_outcome=PredictedOutcome.AVOID,
            supplement=f"parse_error: {e}",
        )


def call_agents_concurrently(
    stock_code: str,
    date: str,
    round_num: int,
    agent_input: dict[str, Any],
    previous_outputs: list[AgentOutput] | None = None,
    timeout: int = 60,
) -> list[AgentOutput]:
    """
    并发调用4个Agent（DD-04 第4.6节）。

    [PRD-T-107] asyncio+aiohttp 并发调用LLM，串行禁止
    [PRD-T-108] 超时60秒跳过该Agent；全部超时降级评分层

    此处使用 threading（同步环境），效果等价于 asyncio.gather。
    """
    agent_names = ["mainline_hunter", "fund_detective", "sentiment_catcher", "experience_judge"]
    results: list[AgentOutput] = []

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                call_single_agent,
                name, stock_code, date, agent_input, round_num,
                previous_outputs, timeout,
            ): name
            for name in agent_names
        }

        for future in concurrent.futures.as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result(timeout=timeout + 10)
                results.append(result)
                logger.info("Agent %s completed: score=%d, confidence=%.2f",
                            agent_name, result.score, result.confidence)
            except Exception as e:
                logger.error("Agent %s failed: %s", agent_name, e)
                results.append(AgentOutput(
                    agent_name=AgentName(agent_name),
                    score=0,
                    buy_reasons=[],
                    against_reasons=[],
                    confidence=0.0,
                    predicted_outcome=PredictedOutcome.AVOID,
                    supplement=f"executor_error: {e}",
                ))

    # 按 Agent 顺序排序
    name_order = {name: i for i, name in enumerate(agent_names)}
    results.sort(key=lambda r: name_order.get(r.agent_name.value, 99))

    # 检查是否全部超时/失败
    valid_count = sum(1 for r in results if r.supplement is None or not r.supplement.startswith(("llm_error", "executor_error", "parse_error")))
    if valid_count == 0 and all(r.score == 0 for r in results):
        logger.error("所有Agent超时/失败")
        raise RuntimeError("所有Agent超时/失败，降级到评分层")

    return results
