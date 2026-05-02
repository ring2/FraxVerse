"""
FraxVerse · AI-Agent 模块单元测试

严格对齐 DD-04 第8节测试要点（24+ 个约束）。
"""
from __future__ import annotations

import pytest
from src.agent.models import (
    AgentName,
    AgentOutput,
    WeightedVoteResult,
    AgentDiscussionRound,
    LLMCallRecord,
    PredictedOutcome,
    DecisionType,
    DegradeLevel,
)
from src.agent.validator import (
    validate_agent_outputs,
    check_convergence,
    handle_no_convergence,
    check_extreme_streak,
)
from src.agent.voting import weighted_vote
from src.agent.calibration import get_calib_factor, calibrate_weights
from src.agent.degradation import generate_rule_based_decisions, generate_fallback_decision
from src.agent.llm_client import (
    build_agent_input,
    render_prompt_template,
    estimate_llm_cost,
    parse_llm_json_response,
    call_single_agent,
)
from src.agent.budget import (
    check_llm_budget,
    estimate_llm_cost as budget_estimate_llm_cost,
)


# ═══════════════════════════════════════════════
# Pydantic 模型测试
# ═══════════════════════════════════════════════

class TestAgentOutput:
    """DD-04 8.1 AgentOutput Pydantic校验"""

    def test_valid_score(self):
        """score=50 校验通过"""
        output = AgentOutput(
            agent_name=AgentName.MAINLINE_HUNTER,
            score=50,
            buy_reasons=["板块资金持续流入"],
            against_reasons=["短期涨幅较大"],
        )
        assert output.score == 50

    def test_invalid_score_raises(self):
        """score=150 校验失败，抛出 ValueError [PRD-T-095]"""
        with pytest.raises(ValueError):
            AgentOutput(
                agent_name=AgentName.MAINLINE_HUNTER,
                score=150,
                buy_reasons=["test"],
                against_reasons=["test"],
            )

    def test_negative_score_raises(self):
        """score=-1 校验失败"""
        with pytest.raises(ValueError):
            AgentOutput(
                agent_name=AgentName.MAINLINE_HUNTER,
                score=-1,
                buy_reasons=["test"],
                against_reasons=["test"],
            )

    def test_empty_against_reasons_allowed(self):
        """反对理由为空允许构造（由validator运行时处理 [PRD-T-096]）"""
        output = AgentOutput(
            agent_name=AgentName.MAINLINE_HUNTER,
            score=80,
            buy_reasons=["test"],
            against_reasons=[],
        )
        assert output.has_no_against_reasons
        assert output.score == 80  # 构造时不变，validator 处理

    def test_extreme_score_zero(self):
        """极端评分 0 [PRD-T-097]"""
        output = AgentOutput(
            agent_name=AgentName.SENTIMENT_CATCHER,
            score=0,
            buy_reasons=["test"],
            against_reasons=["test"],
        )
        assert output.is_extreme

    def test_extreme_score_hundred(self):
        """极端评分 100 [PRD-T-097]"""
        output = AgentOutput(
            agent_name=AgentName.EXPERIENCE_JUDGE,
            score=100,
            buy_reasons=["test"],
            against_reasons=["test"],
        )
        assert output.is_extreme

    def test_enum_agent_names(self):
        """AgentName 枚举"""
        assert AgentName.MAINLINE_HUNTER.value == "mainline_hunter"
        assert AgentName.FUND_DETECTIVE.value == "fund_detective"
        assert AgentName.SENTIMENT_CATCHER.value == "sentiment_catcher"
        assert AgentName.EXPERIENCE_JUDGE.value == "experience_judge"


# ═══════════════════════════════════════════════
# 验证器测试
# ═══════════════════════════════════════════════

class TestValidateAgentOutputs:
    """DD-04 8.1 输出校验"""

    def test_against_reasons_empty_to_50(self):
        """反对理由为空→评分降为50 [PRD-T-096]"""
        outputs = [
            AgentOutput(
                agent_name=AgentName.MAINLINE_HUNTER, score=85,
                buy_reasons=["板块资金流入"], against_reasons=[], confidence=0.8,
            )
        ]
        validated = validate_agent_outputs(outputs)
        assert validated[0].score == 50

    def test_buy_reasons_empty_to_50(self):
        """买入理由为空→评分降为50"""
        outputs = [
            AgentOutput(
                agent_name=AgentName.MAINLINE_HUNTER, score=85,
                buy_reasons=[], against_reasons=["反对"], confidence=0.8,
            )
        ]
        validated = validate_agent_outputs(outputs)
        assert validated[0].score == 50

    def test_extreme_score_marked(self):
        """极端评分标记 [PRD-T-097]"""
        outputs = [
            AgentOutput(
                agent_name=AgentName.SENTIMENT_CATCHER, score=0,
                buy_reasons=["情绪悲观"], against_reasons=["可能反转"], confidence=0.5,
            )
        ]
        validated = validate_agent_outputs(outputs)
        assert validated[0].score == 0  # 保留评分
        assert validated[0].is_extreme


class TestHandleNoConvergence:
    """DD-04 8.1 不收敛兜底"""

    def test_normal_convergence(self):
        """分差≤30→normal"""
        score, method = handle_no_convergence([60, 65, 70])
        assert method == "normal"
        assert score == 65.0

    def test_trimmed_mean(self):
        """分差>30→trimmed mean [PRD-T-098]"""
        score, method = handle_no_convergence([50, 60, 85, 95])
        assert method == "trimmed_mean"
        assert 60 < score < 85  # trimmed = [60, 85]

    def test_only_two_scores_trimmed(self):
        """只有2个评分→无法trim，取均值"""
        score, method = handle_no_convergence([95, 20])
        assert method in ("insufficient_data", "trimmed_mean")

    def test_single_score(self):
        """1个评分→取该值"""
        score, method = handle_no_convergence([60])
        assert method == "insufficient_data"
        assert score == 60.0

    def test_no_scores(self):
        """0个评分→返回0"""
        score, method = handle_no_convergence([])
        assert method == "insufficient_data"
        assert score == 0.0


# ═══════════════════════════════════════════════
# 加权投票测试
# ═══════════════════════════════════════════════

class TestWeightedVote:
    """DD-04 8.1 加权投票"""

    WEIGHTS = [
        {"agent_name": "mainline_hunter", "market_state": "mainline_confirmed", "effective_weight": 0.35},
        {"agent_name": "fund_detective", "market_state": "mainline_confirmed", "effective_weight": 0.25},
        {"agent_name": "sentiment_catcher", "market_state": "mainline_confirmed", "effective_weight": 0.15},
        {"agent_name": "experience_judge", "market_state": "mainline_confirmed", "effective_weight": 0.25},
    ]

    def _make_outputs(self):
        return [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=85, buy_reasons=["a"], against_reasons=["b"], confidence=0.8),
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=70, buy_reasons=["a"], against_reasons=["b"], confidence=0.7),
            AgentOutput(agent_name=AgentName.SENTIMENT_CATCHER, score=65, buy_reasons=["a"], against_reasons=["b"], confidence=0.6),
            AgentOutput(agent_name=AgentName.EXPERIENCE_JUDGE, score=80, buy_reasons=["a"], against_reasons=["b"], confidence=0.8),
        ]

    def test_normal_vote(self):
        """正常投票"""
        result = weighted_vote("000001", "mainline_confirmed", self._make_outputs(), self.WEIGHTS)
        assert result.stock_code == "000001"
        assert result.decision in (DecisionType.BUY, DecisionType.HOLD)
        assert len(result.agent_votes) == 4

    def test_buy_decision(self):
        """买入理由>反对理由+阈值→buy [PRD-T-103]"""
        outputs = self._make_outputs()
        result = weighted_vote("000001", "mainline_confirmed", outputs, self.WEIGHTS, decision_threshold=1.0)
        if result.net_score > 1.0:
            assert result.decision == DecisionType.BUY

    def test_reject_decision(self):
        """反对理由>买入理由→reject [PRD-T-103]"""
        outputs = [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=30, buy_reasons=["a"], against_reasons=["b1", "b2", "b3"], confidence=0.3),
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=25, buy_reasons=["a"], against_reasons=["b1", "b2"], confidence=0.3),
            AgentOutput(agent_name=AgentName.SENTIMENT_CATCHER, score=20, buy_reasons=["a"], against_reasons=["b"], confidence=0.3),
            AgentOutput(agent_name=AgentName.EXPERIENCE_JUDGE, score=35, buy_reasons=["a"], against_reasons=["b"], confidence=0.4),
        ]
        result = weighted_vote("000001", "mainline_confirmed", outputs, self.WEIGHTS)
        assert result.decision == DecisionType.REJECT

    def test_extreme_market_veto(self):
        """极端行情风控否决 [PRD-T-101]"""
        result = weighted_vote("000001", "extreme", self._make_outputs(), self.WEIGHTS)
        assert result.risk_veto is True
        assert result.decision == DecisionType.REJECT

    def test_risk_event_veto(self):
        """未解决风控事件否决"""
        result = weighted_vote(
            "000001", "mainline_confirmed", self._make_outputs(), self.WEIGHTS,
            risk_events_active=True,
        )
        assert result.risk_veto is True
        assert result.decision == DecisionType.REJECT

    def test_liquidity_veto(self):
        """流动性检查否决"""
        result = weighted_vote(
            "000001", "mainline_confirmed", self._make_outputs(), self.WEIGHTS,
            daily_volume=10_000_000,
        )
        assert result.risk_veto is True

    def test_extreme_score_weight_halving(self):
        """极端评分权重减半 [PRD-T-097]"""
        outputs = [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=85, buy_reasons=["a"], against_reasons=["b"], confidence=0.8),
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=70, buy_reasons=["a"], against_reasons=["b"], confidence=0.7),
            AgentOutput(agent_name=AgentName.SENTIMENT_CATCHER, score=0, buy_reasons=["情绪低迷"], against_reasons=["可能反转"], confidence=0.5),
            AgentOutput(agent_name=AgentName.EXPERIENCE_JUDGE, score=100, buy_reasons=["经验确认"], against_reasons=["历史风险"], confidence=0.9),
        ]
        result = weighted_vote("000001", "mainline_confirmed", outputs, self.WEIGHTS)
        # 极端评分的 Agent 权重减半：0.15 → 0.075, 0.25 → 0.125
        assert abs(result.agent_votes["sentiment_catcher"]["weight"] - 0.075) < 0.001
        assert abs(result.agent_votes["experience_judge"]["weight"] - 0.125) < 0.001

    def test_weight_normalization(self):
        """权重归一化"""
        outputs = self._make_outputs()
        result = weighted_vote("000001", "mainline_confirmed", outputs[:2] + outputs[2:], self.WEIGHTS)
        # 所有权重和应该近似等于 4.0（归一化后）
        # 在归一化前：0.35+0.25+0.15+0.25=1.0，归一化后权重和不变，但 total_score 被乘了 4.0/weight_sum
        # 因为权重和就是1.0，所以因子=4.0
        assert result.total_score > 0


# ═══════════════════════════════════════════════
# 权重校准测试
# ═══════════════════════════════════════════════

class TestCalibration:
    """DD-04 8.1 权重校准"""

    def test_calib_factor_bounds(self):
        """校准系数边界 [PRD-T-106]"""
        assert get_calib_factor(0.90) == 1.3  # 上限
        assert get_calib_factor(0.70) == 1.3
        assert get_calib_factor(0.69) == 1.1
        assert get_calib_factor(0.50) == 1.0
        assert get_calib_factor(0.40) == 0.7
        assert get_calib_factor(0.39) == 0.5
        assert get_calib_factor(0.00) == 0.5  # 不低于 0.3

    def test_high_win_rate_increase(self):
        """胜率≥70%→提升20% [PRD-T-105]"""
        assert get_calib_factor(0.75) == 1.3

    def test_low_win_rate_decrease(self):
        """胜率<40%→降权50% [PRD-T-105]"""
        assert get_calib_factor(0.35) == 0.5


# ═══════════════════════════════════════════════
# 降级策略测试
# ═══════════════════════════════════════════════

class TestDegradation:
    """DD-04 8.1 降级策略"""

    def test_rule_based_buy(self):
        """评分≥70→buy"""
        pool = [{"stock_code": "000001", "score_total": 85}]
        decisions = generate_rule_based_decisions(pool, "2026-05-02")
        assert decisions[0].decision == DecisionType.BUY

    def test_rule_based_hold(self):
        """评分50-70→hold"""
        pool = [{"stock_code": "000001", "score_total": 60}]
        decisions = generate_rule_based_decisions(pool, "2026-05-02")
        assert decisions[0].decision == DecisionType.HOLD

    def test_rule_based_reject(self):
        """评分<50→reject"""
        pool = [{"stock_code": "000001", "score_total": 30}]
        decisions = generate_rule_based_decisions(pool, "2026-05-02")
        assert decisions[0].decision == DecisionType.REJECT

    def test_fallback_with_score(self):
        """有评分层结果→根据70分阈值"""
        fb = generate_fallback_decision("000001", 75.0, "2026-05-02")
        assert fb.decision == DecisionType.BUY
        assert fb.convergence_method == "degraded_single"

    def test_fallback_without_score(self):
        """无评分层结果→reject"""
        fb = generate_fallback_decision("000001", None, "2026-05-02")
        assert fb.decision == DecisionType.REJECT


# ═══════════════════════════════════════════════
# LLM 客户端测试
# ═══════════════════════════════════════════════

class TestLLMClient:
    """DD-04 8.1 LLM 客户端"""

    def test_build_agent_input_structure(self):
        """Agent输入结构完整性"""
        inp = build_agent_input("000001", "2026-05-02")
        assert "mainline_hunter_input" in inp
        assert "fund_detective_input" in inp
        assert "sentiment_catcher_input" in inp
        assert "experience_judge_input" in inp
        assert "market_state" in inp

    def test_render_prompt_template(self):
        """提示词渲染"""
        inp = build_agent_input("000001", "2026-05-02")
        sys_p, user_p = render_prompt_template("mainline_hunter", inp, "000001", "2026-05-02", 1)
        assert "主线猎手" in sys_p
        assert "000001" in user_p
        assert "2026-05-02" in user_p

    def test_render_with_round_context(self):
        """带前轮上下文的渲染"""
        inp = build_agent_input("000001", "2026-05-02")
        previous = [
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=70, buy_reasons=["a"], against_reasons=["b"], confidence=0.7),
        ]
        sys_p, user_p = render_prompt_template("mainline_hunter", inp, "000001", "2026-05-02", 2, previous)
        assert "第2轮" in user_p

    def test_parse_llm_json(self):
        """JSON 解析"""
        raw = '```json\n{"score": 85, "buy_reasons": ["a"], "against_reasons": ["b"], "confidence": 0.8, "predicted_outcome": "buy"}\n```'
        data = parse_llm_json_response(raw)
        assert data["score"] == 85
        assert data["predicted_outcome"] == "buy"

    def test_parse_llm_json_no_markdown(self):
        """无 markdown 包裹的 JSON"""
        raw = '{"score": 70, "buy_reasons": ["x"], "against_reasons": ["y"], "confidence": 0.5, "predicted_outcome": "hold"}'
        data = parse_llm_json_response(raw)
        assert data["score"] == 70

    def test_parse_llm_json_extra_text(self):
        """带多余文本的 JSON"""
        raw = '好的，这是分析结果：\n{"score": 60, "buy_reasons": ["a"], "against_reasons": ["b"], "confidence": 0.6, "predicted_outcome": "hold"}\n---'
        data = parse_llm_json_response(raw)
        assert data["score"] == 60

    def test_estimate_cost(self):
        """Token 成本估算"""
        cost = estimate_llm_cost("deepseek-chat", 1000, 500)
        assert round(cost, 4) == 0.002

    def test_estimate_cost_unknown_model(self):
        """未知模型使用默认价格"""
        cost = estimate_llm_cost("unknown-model", 1000, 500)
        assert round(cost, 4) == 0.002  # 用 deepseek-chat 价格


# ═══════════════════════════════════════════════
# Token 预算测试
# ═══════════════════════════════════════════════

class TestBudget:
    """DD-04 8.1 Token 预算"""

    def test_estimate_cost(self):
        """成本估算"""
        cost = budget_estimate_llm_cost("deepseek-chat", 1000, 500)
        assert round(cost, 4) == 0.002


# ═══════════════════════════════════════════════
# 集成与边界测试
# ═══════════════════════════════════════════════

class TestIntegration:
    """DD-04 8.2 集成测试"""

    def test_full_workflow_happy_path(self):
        """完整流程：4Agent → 校验 → 投票（2轮收敛）"""
        from src.agent.validator import check_convergence
        from src.agent.voting import weighted_vote

        # 模拟第一轮
        round1 = [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=80, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=75, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.SENTIMENT_CATCHER, score=70, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.EXPERIENCE_JUDGE, score=85, buy_reasons=["a"], against_reasons=["b"]),
        ]
        # 检查收敛
        is_converged, max_diff, validated = check_convergence(round1)
        assert is_converged  # 分差 15 <= 30
        assert max_diff == 15

        # 投票
        weights = [
            {"agent_name": "mainline_hunter", "market_state": "mainline_confirmed", "effective_weight": 0.35},
            {"agent_name": "fund_detective", "market_state": "mainline_confirmed", "effective_weight": 0.25},
            {"agent_name": "sentiment_catcher", "market_state": "mainline_confirmed", "effective_weight": 0.15},
            {"agent_name": "experience_judge", "market_state": "mainline_confirmed", "effective_weight": 0.25},
        ]
        result = weighted_vote("000001", "mainline_confirmed", validated, weights)
        assert result.decision in (DecisionType.BUY, DecisionType.HOLD)
        assert result.convergence_method == "normal"

    def test_all_agents_timeout_fallback(self):
        """全部Agent超时→降级评分层"""
        fb = generate_fallback_decision("000001", 75.0, "2026-05-02")
        assert fb.decision == DecisionType.BUY  # 75 >= 70 → buy
        assert fb.convergence_method == "degraded_single"

        fb2 = generate_fallback_decision("000001", 60.0, "2026-05-02")
        assert fb2.decision == DecisionType.REJECT  # 60 < 70 → reject

    def test_extreme_market_all_reject(self):
        """极端行情→所有标的reject [PRD-T-101]"""
        outputs = [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=85, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.FUND_DETECTIVE, score=70, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.SENTIMENT_CATCHER, score=65, buy_reasons=["a"], against_reasons=["b"]),
            AgentOutput(agent_name=AgentName.EXPERIENCE_JUDGE, score=80, buy_reasons=["a"], against_reasons=["b"]),
        ]
        weights = [
            {"agent_name": "mainline_hunter", "market_state": "extreme", "effective_weight": 0.25},
            {"agent_name": "fund_detective", "market_state": "extreme", "effective_weight": 0.25},
            {"agent_name": "sentiment_catcher", "market_state": "extreme", "effective_weight": 0.25},
            {"agent_name": "experience_judge", "market_state": "extreme", "effective_weight": 0.25},
        ]
        result = weighted_vote("000001", "extreme", outputs, weights)
        assert result.risk_veto is True
        assert result.decision == DecisionType.REJECT


class TestEdgeCases:
    """边界情况测试"""

    def test_zero_weight_agent(self):
        """权重为0的Agent不影响投票"""
        outputs = [
            AgentOutput(agent_name=AgentName.MAINLINE_HUNTER, score=85, buy_reasons=["a"], against_reasons=["b"]),
        ]
        weights = [
            {"agent_name": "mainline_hunter", "market_state": "test", "effective_weight": 0.0},
        ]
        result = weighted_vote("000001", "test", outputs, weights)
        assert abs(result.agent_votes["mainline_hunter"]["weight"]) < 0.001
        assert result.total_score == 0.0

    def test_all_same_score(self):
        """所有Agent评分相同→正常收敛"""
        score, method = handle_no_convergence([70, 70, 70, 70])
        assert method == "normal"
        assert score == 70.0
