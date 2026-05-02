"""
FraxVerse · Agent 主调度器

严格按 DD-04-AI-Agent模块.md 第4.4~4.5节和第4.13节实现。

负责：
1. 每日讨论调度（先校准权重 → 检查预算 → 风控前置 → 并发讨论 → 写入DB）
2. 单只标的讨论流程（组装输入 → 多轮讨论 → 加权投票）
3. 实际结果回填与胜率更新
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable

from src.agent.models import (
    AgentName,
    AgentOutput,
    DecisionType,
    WeightedVoteResult,
)
from src.agent.llm_client import (
    build_agent_input,
    call_agents_concurrently,
)
from src.agent.validator import (
    check_convergence,
    check_extreme_streak,
    validate_agent_outputs,
)
from src.agent.voting import weighted_vote
from src.agent.calibration import calibrate_weights
from src.agent.budget import check_llm_budget, get_degrade_level
from src.agent.degradation import (
    generate_rule_based_decisions,
    generate_fallback_decision,
)
from src.agent.models import DegradeLevel

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent 主调度器。

    对应 DD-04 第4.4节 run_agent_discussion 主流程。
    负责将前面所有模块串起来执行完整 Agent 分析链路。
    """

    def __init__(
        self,
        # 数据库操作接口（注入而非直接依赖，便于测试）
        get_stock_pool_fn: Callable[[str], list[dict[str, Any]]],
        get_market_state_fn: Callable[[str], str | None],
        get_weights_fn: Callable[[str], list[dict[str, Any]]],
        get_active_risk_events_fn: Callable[[str], bool],
        get_daily_volume_fn: Callable[[str, str], float | None],
        get_agent_history_fn: Callable[[str], list[dict[str, Any]]],
        save_decisions_fn: Callable[[str, list[WeightedVoteResult]], None],
        save_discussions_fn: Callable[[str, str, list[list[AgentOutput]]], None],
        update_weights_fn: Callable[[str, str, float, float, float, int], None],
        get_all_weights_fn: Callable[[str], list[dict[str, Any]]],
        update_weight_db_fn: Callable[[str, str, float, float, float, int], None],
        update_outcome_fn: Callable[[int, str, str], None],
        get_pending_records_fn: Callable[[str], list[dict[str, Any]]],
        get_kline_close_fn: Callable[[str, str], float | None],
        get_recent_scores_fn: Callable[[str], list[int]] | None = None,
    ):
        self.get_stock_pool = get_stock_pool_fn
        self.get_market_state = get_market_state_fn
        self.get_weights = get_weights_fn
        self.get_active_risk_events = get_active_risk_events_fn
        self.get_daily_volume = get_daily_volume_fn
        self.get_agent_history = get_agent_history_fn
        self.save_decisions = save_decisions_fn
        self.save_discussions = save_discussions_fn
        self.update_weights = update_weights_fn
        self.get_all_weights = get_all_weights_fn
        self.update_weight_db = update_weight_db_fn
        self.update_outcome = update_outcome_fn
        self.get_pending_records = get_pending_records_fn
        self.get_kline_close = get_kline_close_fn
        self.get_recent_scores = get_recent_scores_fn

    def run_daily_analysis(
        self,
        analysis_date: str | None = None,
        stock_codes: list[str] | None = None,
    ) -> list[WeightedVoteResult]:
        """
        每日 Agent 分析主流程（DD-04 第4.4节 run_agent_discussion）。

        Args:
            analysis_date: 分析日期（默认今天）
            stock_codes: 指定标的列表（默认从股票池读取）

        Returns:
            决策结果列表
        """
        dt = analysis_date or date.today().isoformat()

        # ──── 前置检查：Token预算 [PRD-T-113] ────
        if not check_llm_budget():
            logger.warning("Token预算超限，降级为纯规则模式")
            return self._degraded_decision(dt, stock_codes)

        # ──── 前置检查：LLM可用性（通过降级等级判断）[PRD-T-111] ────
        degrade_level = get_degrade_level()
        if degrade_level == DegradeLevel.FULL:
            logger.warning("LLM不可用(降级等级=%s)，降级为纯规则模式", degrade_level)
            return self._degraded_decision(dt, stock_codes)

        # ──── 获取市场状态 ────
        market_state = self.get_market_state(dt)
        if not market_state:
            market_state = "mainline_confirmed"

        # ──── 风控前置检查 [PRD-T-101] ────
        if market_state == "extreme":
            logger.warning("极端行情，风控一票否决")
            return self._extreme_veto(dt, stock_codes)

        # ──── 执行权重校准（投票前校准） ────
        try:
            calibrate_weights(
                date=dt,
                get_agent_history_fn=self.get_agent_history,
                get_all_weights_fn=self.get_all_weights,
                update_weight_fn=self.update_weight_db,
            )
        except Exception as e:
            logger.warning("权重校准失败，使用现有权重继续: %s", e)

        # ──── 确定分析标的 ────
        if stock_codes is None:
            pool = self.get_stock_pool(dt)
            stock_codes = [p.get("stock_code", "") for p in pool if p.get("stock_code")]
            logger.info("从股票池读取 %d 只标的", len(stock_codes))

        if not stock_codes:
            logger.info("无待分析标的")
            return []

        # ──── 根据降级等级调整讨论参数 ────
        max_rounds, scope = self._get_degrade_params(degrade_level)
        if scope == "partial" and len(stock_codes) > 5:
            # 只分析评分前5名
            pool = self.get_stock_pool(dt)
            pool.sort(key=lambda p: float(p.get("score_total", 0)), reverse=True)
            stock_codes = [p["stock_code"] for p in pool[:5] if p.get("stock_code")]

        # ──── 并发调度所有标的的 Agent 讨论 ────
        all_decisions: list[WeightedVoteResult] = []
        all_discussions: list[tuple[str, list[list[AgentOutput]]]] = []  # (stock_code, rounds)

        for code in stock_codes:
            try:
                decision, round_outputs = self._discuss_single_stock(
                    stock_code=code,
                    date=dt,
                    market_state=market_state,
                    max_rounds=max_rounds,
                )
                all_decisions.append(decision)
                all_discussions.append((code, round_outputs))
            except Exception as e:
                logger.error("标的 %s 讨论异常: %s", code, e)
                fallback = generate_fallback_decision(code, None, dt)
                all_decisions.append(fallback)

        # ──── 批量写入数据库 ────
        try:
            self.save_decisions(dt, all_decisions)
            for code, rounds in all_discussions:
                self.save_discussions(dt, code, rounds)
        except Exception as e:
            logger.error("保存决策到数据库失败: %s", e)

        logger.info("每日分析完成: %s, 共 %d 只标的", dt, len(all_decisions))
        return all_decisions

    def _discuss_single_stock(
        self,
        stock_code: str,
        date: str,
        market_state: str,
        max_rounds: int = 3,
    ) -> tuple[WeightedVoteResult, list[list[AgentOutput]]]:
        """
        单只标的讨论流程（DD-04 第4.5节 discuss_single_stock）。

        Returns:
            (决策结果, 各轮 Agent 输出)
        """
        # 1. 组装 Agent 输入
        agent_input = build_agent_input(stock_code, date)

        # 2. 读取当前权重
        weights = self.get_weights(market_state)

        # 3. 多轮讨论循环 [PRD-T-094] 2-3轮
        all_round_outputs: list[list[AgentOutput]] = []
        previous_outputs: list[AgentOutput] | None = None
        convergence_method = "normal"

        for round_num in range(1, min(max_rounds, 3) + 1):
            # 3a. 并发调用4个Agent [PRD-T-107]
            round_outputs = call_agents_concurrently(
                stock_code=stock_code,
                date=date,
                round_num=round_num,
                agent_input=agent_input,
                previous_outputs=previous_outputs,
            )

            # 3b. 收敛检查
            is_converged, max_diff, validated = check_convergence(round_outputs)
            all_round_outputs.append(validated)

            if is_converged:
                logger.info("标的 %s 第%d轮收敛(分差=%d)", stock_code, round_num, max_diff)
                previous_outputs = validated
                break

            # 3c. 不收敛→准备下一轮
            previous_outputs = validated
            logger.info("标的 %s 第%d轮未收敛(分差=%d)，继续讨论", stock_code, round_num, max_diff)

            if round_num == max_rounds:
                # 最大轮次仍不收敛 → trimmed mean [PRD-T-098]
                logger.warning("标的 %s %d轮不收敛", stock_code, max_rounds)
                convergence_method = "trimmed_mean"

        # 极端评分检查 [PRD-T-099]
        try:
            alerts = check_extreme_streak(previous_outputs or [], self.get_recent_scores)
            for alert in alerts:
                if alert["action"] == "degrade_50pct":
                    agent_name = alert["agent_name"]
                    for ms in ["mainline_confirmed", "oscillating"]:
                        weights_list = self.get_all_weights(ms)
                        for w in weights_list:
                            if w.get("agent_name") == agent_name:
                                old_calib = float(w.get("calib_factor", 1.0))
                                new_calib = old_calib * 0.5
                                self.update_weights(
                                    agent_name, ms, new_calib,
                                    float(w.get("base_weight", 0.25)) * new_calib,
                                    float(w.get("win_rate", 0.5)),
                                    int(w.get("recent_count", 0)),
                                )
                                logger.warning(
                                    "Agent %s 连续极端评分，降权50%% (%s → %s)",
                                    agent_name, old_calib, new_calib,
                                )
        except Exception as e:
            logger.warning("极端评分检查失败: %s", e)

        # 4. 加权投票
        final_outputs = all_round_outputs[-1] if all_round_outputs else []
        risk_events_active = self.get_active_risk_events(date)
        daily_volume = self.get_daily_volume(stock_code, date)

        decision = weighted_vote(
            stock_code=stock_code,
            market_state=market_state,
            outputs=final_outputs,
            weights=weights,
            convergence_method=convergence_method,
            risk_events_active=risk_events_active,
            daily_volume=daily_volume,
        )

        return decision, all_round_outputs

    def _degraded_decision(
        self,
        date: str,
        stock_codes: list[str] | None,
    ) -> list[WeightedVoteResult]:
        """降级到纯规则模式"""
        if stock_codes is None:
            pool = self.get_stock_pool(date)
        else:
            pool = [{"stock_code": code, "score_total": 0} for code in stock_codes]
            # 尝试从数据库获取实际评分
            db_pool = self.get_stock_pool(date)
            pool_map = {p.get("stock_code", ""): p for p in db_pool}
            for p in pool:
                code = p["stock_code"]
                if code in pool_map:
                    p["score_total"] = pool_map[code].get("score_total", 0)

        return generate_rule_based_decisions(pool, date)

    def _extreme_veto(
        self,
        date: str,
        stock_codes: list[str] | None,
    ) -> list[WeightedVoteResult]:
        """极端行情风控一票否决"""
        if stock_codes is None:
            pool = self.get_stock_pool(date)
            stock_codes = [p.get("stock_code", "") for p in pool if p.get("stock_code")]

        return [
            WeightedVoteResult(
                stock_code=code,
                total_score=0,
                buy_score_sum=0,
                against_score_sum=0,
                net_score=0,
                decision=DecisionType.REJECT,
                agent_votes={},
                risk_veto=True,
                risk_veto_reason="极端行情，风控一票否决",
                convergence_method="risk_veto",
            )
            for code in stock_codes
        ]

    def _get_degrade_params(self, level: DegradeLevel) -> tuple[int, str]:
        """根据降级等级返回讨论参数"""
        params = {
            DegradeLevel.NONE: (3, "full"),
            DegradeLevel.LIGHT: (2, "full"),
            DegradeLevel.PARTIAL: (1, "partial"),
            DegradeLevel.FULL: (0, "none"),
        }
        return params.get(level, (3, "full"))

    # ─────────────────────────────────────────────
    # 4.13 实际结果回填与胜率更新
    # ─────────────────────────────────────────────

    def update_actual_outcomes(self, analysis_date: str | None = None) -> int:
        """
        每日收盘后，回填Agent推荐的actual_outcome（DD-04 第4.13节）。

        用于滚动胜率计算。

        Args:
            analysis_date: 回填日期（默认今天）

        Returns:
            更新记录数
        """
        dt = analysis_date or date.today().isoformat()
        target_date = dt

        # 查询所有 pending 的推荐记录
        pending = self.get_pending_records(target_date)

        if not pending:
            logger.info("无待回填的推荐记录")
            return 0

        updated_count = 0
        for record in pending:
            record_id = record.get("id")
            stock_code = record.get("stock_code", "")
            record_date = record.get("date", "")

            if not record_id or not stock_code or not record_date:
                continue

            # 获取买入日收盘价
            buy_close = self.get_kline_close(stock_code, record_date)
            if buy_close is None:
                continue

            # 获取 T+1 日收盘价
            next_date = (datetime.strptime(record_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            next_close = self.get_kline_close(stock_code, next_date)
            if next_close is None:
                continue

            # 判断胜负：T+1 收盘价 > 买入日收盘价
            pnl_pct = (next_close - buy_close) / buy_close
            actual = "win" if pnl_pct > 0 else "loss"

            self.update_outcome(record_id, actual, dt)
            updated_count += 1

        # 更新完成后触发权重校准（使用昨天之前的数据）
        yesterday = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            calibrate_weights(
                date=yesterday,
                get_agent_history_fn=self.get_agent_history,
                get_all_weights_fn=self.get_all_weights,
                update_weight_fn=self.update_weight_db,
            )
        except Exception as e:
            logger.warning("回填后权重校准失败: %s", e)

        logger.info("实际结果回填完成: %d 条记录", updated_count)
        return updated_count
