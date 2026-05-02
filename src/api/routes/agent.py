"""
FraxVerse · Agent API 路由

严格按 DD-04-AI-Agent模块.md 第3节 API 契约实现。

端点总览：
  GET    /api/v1/agent/discussions         查询讨论记录
  GET    /api/v1/agent/discussions/{date}/{stock_code} 查询讨论详情
  GET    /api/v1/agent/decisions            查询决策记录
  GET    /api/v1/agent/decisions/{date}     查询某日决策
  GET    /api/v1/agent/weights             查询当前权重配置
  PUT    /api/v1/agent/weights             更新基准权重
  POST   /api/v1/agent/trigger             手动触发Agent分析
  GET    /api/v1/agent/calibration         查询校准面板数据
  GET    /api/v1/agent/llm-usage           查询LLM用量统计
  PUT    /api/v1/agent/llm-budget          设置Token预算
  GET    /api/v1/agent/prompts             查询提示词列表
  PUT    /api/v1/agent/prompts/{id}/activate 激活提示词版本
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.db.session import get_session
from src.agent.models import DegradeLevel
from src.agent.orchestrator import AgentOrchestrator
from src.agent.budget import get_budget_status, check_budget_and_degrade_if_needed
from src.agent.calibration import calibrate_weights, get_calib_factor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent AI 分析"])


# ─────────────────────────────────────────────
# 辅助函数：数据库操作回调
# ─────────────────────────────────────────────

def _get_orchestrator() -> type[AgentOrchestrator]:
    """获取调度器（延迟初始化，依赖注入）"""
    return AgentOrchestrator


def _get_sync_session():
    """获取同步数据库会话"""
    with get_session() as session:
        yield session


# ─── 数据库操作回调实现 ───

def _make_get_stock_pool(session: Session):
    def fn(dt: str) -> list[dict[str, Any]]:
        rows = session.execute(
            text("SELECT stock_code, score_total FROM stock_pool WHERE date = :date"),
            {"date": dt},
        ).fetchall()
        return [{"stock_code": r[0], "score_total": r[1]} for r in rows]
    return fn


def _make_get_market_state(session: Session):
    def fn(dt: str) -> str | None:
        row = session.execute(
            text("SELECT to_state FROM market_state_log WHERE date <= :date ORDER BY date DESC LIMIT 1"),
            {"date": dt},
        ).fetchone()
        return row[0] if row else None
    return fn


def _make_get_weights(session: Session):
    def fn(market_state: str) -> list[dict[str, Any]]:
        rows = session.execute(
            text("SELECT agent_name, market_state, base_weight, calib_factor, effective_weight, "
                 "win_rate, recent_count, extreme_count, is_degraded "
                 "FROM agent_weights WHERE market_state = :ms"),
            {"ms": market_state},
        ).fetchall()
        return [dict(r._mapping) for r in rows]
    return fn


def _make_get_active_risk_events(session: Session):
    def fn(dt: str) -> bool:
        row = session.execute(
            text("SELECT COUNT(*) FROM risk_events WHERE date = :date AND is_resolved = FALSE LIMIT 1"),
            {"date": dt},
        ).fetchone()
        return row[0] > 0 if row else False
    return fn


def _make_get_daily_volume(session: Session):
    def fn(stock_code: str, dt: str) -> float | None:
        row = session.execute(
            text("SELECT avg_amount FROM fund_flows WHERE stock_code = :code AND date = :date LIMIT 1"),
            {"code": stock_code, "date": dt},
        ).fetchone()
        return float(row[0]) if row else None
    return fn


def _make_get_agent_history(session: Session):
    def fn(agent_name: str) -> list[dict[str, Any]]:
        rows = session.execute(
            text("SELECT predicted_outcome, actual_outcome FROM agent_discussions "
                 "WHERE agent_name = :name AND predicted_outcome IS NOT NULL "
                 "AND actual_outcome IN ('win', 'loss') "
                 "ORDER BY created_at DESC LIMIT 20"),
            {"name": agent_name},
        ).fetchall()
        return [{"predicted_outcome": r[0], "actual_outcome": r[1]} for r in rows]
    return fn


def _make_save_decisions(session: Session):
    def fn(dt: str, decisions: list[Any]) -> None:
        for d in decisions:
            session.execute(
                text("INSERT INTO agent_decisions (date, stock_code, total_score, "
                     "buy_score_sum, against_score_sum, net_score, decision, decision_reason, "
                     "agent_votes_json, risk_veto, risk_veto_reason, convergence_rounds, "
                     "convergence_method, created_at, updated_at) "
                     "VALUES (:date, :stock_code, :total_score, :buy_score_sum, :against_score_sum, "
                     ":net_score, :decision, :decision_reason, :agent_votes, :risk_veto, "
                     ":risk_veto_reason, :convergence_rounds, :convergence_method, NOW(), NOW()) "
                     "ON CONFLICT (date, stock_code) DO UPDATE SET "
                     "total_score = EXCLUDED.total_score, decision = EXCLUDED.decision, "
                     "updated_at = NOW()"),
                {
                    "date": dt,
                    "stock_code": d.stock_code,
                    "total_score": d.total_score,
                    "buy_score_sum": d.buy_score_sum,
                    "against_score_sum": d.against_score_sum,
                    "net_score": d.net_score,
                    "decision": d.decision.value,
                    "decision_reason": d.decision_reason,
                    "agent_votes": str(d.agent_votes),
                    "risk_veto": d.risk_veto,
                    "risk_veto_reason": d.risk_veto_reason,
                    "convergence_rounds": 0,
                    "convergence_method": d.convergence_method,
                },
            )
        session.commit()
    return fn


def _make_save_discussions(session: Session):
    def fn(dt: str, stock_code: str, round_outputs: list[list[Any]]) -> None:
        for round_num, outputs in enumerate(round_outputs, 1):
            for output in outputs:
                session.execute(
                    text("INSERT INTO agent_discussions "
                         "(date, stock_code, round_num, agent_name, score, buy_reasons, "
                         "against_reasons, confidence, predicted_outcome, is_valid, "
                         "invalid_reason, created_at, updated_at) "
                         "VALUES (:date, :stock_code, :round_num, :agent_name, :score, "
                         ":buy_reasons, :against_reasons, :confidence, :predicted_outcome, "
                         ":is_valid, :invalid_reason, NOW(), NOW())"),
                    {
                        "date": dt,
                        "stock_code": stock_code,
                        "round_num": round_num,
                        "agent_name": output.agent_name.value,
                        "score": output.score,
                        "buy_reasons": str(list(output.buy_reasons)),
                        "against_reasons": str(list(output.against_reasons)),
                        "confidence": output.confidence,
                        "predicted_outcome": output.predicted_outcome.value,
                        "is_valid": True,
                        "invalid_reason": None,
                    },
                )
        session.commit()
    return fn


def _make_update_weight(session: Session):
    def fn(agent_name: str, market_state: str, calib_factor: float,
           effective_weight: float, win_rate: float, recent_count: int) -> None:
        session.execute(
            text("UPDATE agent_weights SET calib_factor = :calib, "
                 "effective_weight = :eff, win_rate = :wr, "
                 "recent_count = :rc, updated_at = NOW() "
                 "WHERE agent_name = :name AND market_state = :ms"),
            {
                "calib": calib_factor,
                "eff": effective_weight,
                "wr": win_rate,
                "rc": recent_count,
                "name": agent_name,
                "ms": market_state,
            },
        )
        session.commit()
    return fn


def _make_get_all_weights(session: Session):
    def fn(market_state: str) -> list[dict[str, Any]]:
        rows = session.execute(
            text("SELECT id, agent_name, market_state, base_weight, calib_factor, "
                 "effective_weight, win_rate, recent_count "
                 "FROM agent_weights WHERE market_state = :ms"),
            {"ms": market_state},
        ).fetchall()
        return [dict(r._mapping) for r in rows]
    return fn


def _make_update_weight_db(session: Session):
    return _make_update_weight(session)


def _make_get_pending_records(session: Session):
    def fn(dt: str) -> list[dict[str, Any]]:
        rows = session.execute(
            text("SELECT id, stock_code, date, predicted_outcome FROM agent_discussions "
                 "WHERE predicted_outcome = 'buy' AND actual_outcome = 'pending' "
                 "AND date <= :date - INTERVAL '1 day'"),
            {"date": dt},
        ).fetchall()
        return [{"id": r[0], "stock_code": r[1], "date": r[2].isoformat() if hasattr(r[2], 'isoformat') else r[2]} for r in rows]
    return fn


def _make_get_kline_close(session: Session):
    def fn(stock_code: str, dt: str) -> float | None:
        row = session.execute(
            text("SELECT close FROM daily_klines WHERE stock_code = :code AND date = :date"),
            {"code": stock_code, "date": dt},
        ).fetchone()
        return float(row[0]) if row else None
    return fn


def _make_get_recent_scores(session: Session):
    def fn(agent_name: str) -> list[int]:
        rows = session.execute(
            text("SELECT score FROM agent_discussions "
                 "WHERE agent_name = :name AND is_valid = TRUE "
                 "ORDER BY created_at DESC LIMIT 5"),
            {"name": agent_name},
        ).fetchall()
        return [r[0] for r in rows]
    return fn


def _create_orchestrator(session: Session) -> AgentOrchestrator:
    """用当前会话创建调度器实例"""
    return AgentOrchestrator(
        get_stock_pool_fn=_make_get_stock_pool(session),
        get_market_state_fn=_make_get_market_state(session),
        get_weights_fn=_make_get_weights(session),
        get_active_risk_events_fn=_make_get_active_risk_events(session),
        get_daily_volume_fn=_make_get_daily_volume(session),
        get_agent_history_fn=_make_get_agent_history(session),
        save_decisions_fn=_make_save_decisions(session),
        save_discussions_fn=_make_save_discussions(session),
        update_weights_fn=_make_update_weight(session),
        get_all_weights_fn=_make_get_all_weights(session),
        update_weight_db_fn=_make_update_weight_db(session),
        update_outcome_fn=lambda rid, actual, dt: session.execute(
            text("UPDATE agent_discussions SET actual_outcome = :actual, "
                 "outcome_updated_at = NOW() WHERE id = :id"),
            {"actual": actual, "id": rid},
        ),
        get_pending_records_fn=_make_get_pending_records(session),
        get_kline_close_fn=_make_get_kline_close(session),
        get_recent_scores_fn=_make_get_recent_scores(session),
    )


# ─────────────────────────────────────────────
# API 端点实现
# ─────────────────────────────────────────────

@router.get("/discussions")
def query_discussions(
    date_param: str | None = Query(None, alias="date", description="讨论日期(YYYY-MM-DD)"),
    stock_code: str | None = Query(None, description="股票代码"),
    agent_name: str | None = Query(None, description="Agent名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(_get_sync_session),
):
    """查询讨论记录 [DD-04 3.2节]"""
    dt = date_param or date.today().isoformat()

    conditions = ["date = :date"]
    params: dict[str, Any] = {"date": dt}

    if stock_code:
        conditions.append("stock_code = :stock_code")
        params["stock_code"] = stock_code
    if agent_name:
        conditions.append("agent_name = :agent_name")
        params["agent_name"] = agent_name

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    count = session.execute(
        text(f"SELECT COUNT(*) FROM agent_discussions WHERE {where}"),
        params,
    ).scalar() or 0

    rows = session.execute(
        text(f"SELECT id, date, stock_code, round_num, agent_name, score, "
             f"buy_reasons, against_reasons, confidence, is_valid, "
             f"predicted_outcome, actual_outcome, prompt_tokens, "
             f"completion_tokens, model_name, created_at "
             f"FROM agent_discussions WHERE {where} "
             f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "date": str(r[1]) if r[1] else None,
            "stockCode": r[2],
            "roundNum": r[3],
            "agentName": r[4],
            "score": r[5],
            "buyReasons": r[6] if isinstance(r[6], list) else [],
            "againstReasons": r[7] if isinstance(r[7], list) else [],
            "confidence": float(r[8]) if r[8] else 0,
            "isValid": r[9],
            "predictedOutcome": r[10],
            "actualOutcome": r[11],
            "promptTokens": r[12] or 0,
            "completionTokens": r[13] or 0,
            "modelName": r[14],
            "createdAt": r[15].isoformat() if r[15] else None,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": count,
            "page": page,
            "pageSize": page_size,
            "totalPages": max(1, -(-count // page_size)),
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/discussions/{dt}/{code}")
def query_discussion_detail(
    dt: str,
    code: str,
    session: Session = Depends(_get_sync_session),
):
    """查询某日某标讨论详情 [DD-04 3.2节]"""
    rows = session.execute(
        text("SELECT id, round_num, agent_name, score, buy_reasons, against_reasons, "
             "confidence, is_valid, predicted_outcome, prompt_tokens, completion_tokens, "
             "model_name, raw_response, created_at "
             "FROM agent_discussions WHERE date = :date AND stock_code = :code "
             "ORDER BY round_num, agent_name"),
        {"date": dt, "code": code},
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="讨论记录不存在")

    rounds: dict[int, list] = {}
    for r in rows:
        round_num = r[1]
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append({
            "id": r[0],
            "agentName": r[2],
            "score": r[3],
            "buyReasons": r[4] if isinstance(r[4], list) else [],
            "againstReasons": r[5] if isinstance(r[5], list) else [],
            "confidence": float(r[6]) if r[6] else 0,
            "isValid": r[7],
            "predictedOutcome": r[8],
            "promptTokens": r[9] or 0,
            "completionTokens": r[10] or 0,
            "modelName": r[11],
            "createdAt": r[13].isoformat() if r[13] else None,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "date": dt,
            "stockCode": code,
            "rounds": [{"roundNum": rn, "outputs": outputs} for rn, outputs in sorted(rounds.items())],
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/decisions")
def query_decisions(
    date_param: str | None = Query(None, alias="date", description="决策日期(YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(_get_sync_session),
):
    """查询决策记录 [DD-04 3.3节]"""
    dt = date_param or date.today().isoformat()
    offset = (page - 1) * page_size

    count = session.execute(
        text("SELECT COUNT(*) FROM agent_decisions WHERE date = :date"),
        {"date": dt},
    ).scalar() or 0

    rows = session.execute(
        text("SELECT id, date, stock_code, total_score, buy_score_sum, against_score_sum, "
             "net_score, decision, decision_reason, agent_votes_json, risk_veto, "
             "risk_veto_reason, convergence_rounds, convergence_method, created_at "
             "FROM agent_decisions WHERE date = :date "
             "ORDER BY total_score DESC LIMIT :limit OFFSET :offset"),
        {"date": dt, "limit": page_size, "offset": offset},
    ).fetchall()

    decisions = []
    for r in rows:
        decisions.append({
            "id": r[0],
            "stockCode": r[2],
            "totalScore": float(r[3]) if r[3] else 0,
            "buyScoreSum": float(r[4]) if r[4] else 0,
            "againstScoreSum": float(r[5]) if r[5] else 0,
            "netScore": float(r[6]) if r[6] else 0,
            "decision": r[7],
            "decisionReason": r[8],
            "riskVeto": r[10],
            "riskVetoReason": r[11],
            "convergenceRounds": r[12] or 0,
            "convergenceMethod": r[13],
            "agentVotes": r[9] if isinstance(r[9], dict) else {},
            "createdAt": r[14].isoformat() if r[14] else None,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "date": dt,
            "decisions": decisions,
            "total": count,
            "page": page,
            "pageSize": page_size,
            "totalPages": max(1, -(-count // page_size)),
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/decisions/{dt}")
def query_decisions_by_date(
    dt: str,
    session: Session = Depends(_get_sync_session),
):
    """查询某日决策 [DD-04 3.3节]"""
    rows = session.execute(
        text("SELECT stock_code, total_score, buy_score_sum, against_score_sum, net_score, "
             "decision, decision_reason, risk_veto, risk_veto_reason, convergence_rounds, "
             "convergence_method, agent_votes_json "
             "FROM agent_decisions WHERE date = :date "
             "ORDER BY total_score DESC"),
        {"date": dt},
    ).fetchall()

    decisions = []
    for r in rows:
        decisions.append({
            "stockCode": r[0],
            "totalScore": float(r[1]) if r[1] else 0,
            "buyScoreSum": float(r[2]) if r[2] else 0,
            "againstScoreSum": float(r[3]) if r[3] else 0,
            "netScore": float(r[4]) if r[4] else 0,
            "decision": r[5],
            "decisionReason": r[6],
            "riskVeto": r[7],
            "riskVetoReason": r[8],
            "convergenceRounds": r[9] or 0,
            "convergenceMethod": r[10],
            "agentVotes": r[11] if isinstance(r[11], dict) else {},
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "date": dt,
            "decisions": decisions,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/weights")
def query_weights(
    session: Session = Depends(_get_sync_session),
):
    """查询当前权重配置 [DD-04 3.4节]"""
    rows = session.execute(
        text("SELECT agent_name, market_state, base_weight, calib_factor, effective_weight, "
             "win_rate, recent_count, extreme_count, is_degraded "
             "FROM agent_weights ORDER BY market_state, agent_name"),
    ).fetchall()

    # 获取当前市场状态
    current_ms = session.execute(
        text("SELECT to_state FROM market_state_log ORDER BY date DESC LIMIT 1"),
    ).scalar() or "mainline_confirmed"

    weights = []
    for r in rows:
        weights.append({
            "agentName": r[0],
            "marketState": r[1],
            "baseWeight": float(r[2]) if r[2] else 0,
            "calibFactor": float(r[3]) if r[3] else 1.0,
            "effectiveWeight": float(r[4]) if r[4] else 0,
            "winRate": float(r[5]) if r[5] else 0.5,
            "recentCount": r[6] or 0,
            "extremeCount": r[7] or 0,
            "isDegraded": r[8] or False,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "weights": weights,
            "currentMarketState": current_ms,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/weights")
def update_weights(
    body: dict[str, Any],
    session: Session = Depends(_get_sync_session),
):
    """更新基准权重 [DD-04 3.5节]"""
    weights_data = body.get("weights", [])

    for w in weights_data:
        agent_name = w.get("agentName")
        market_state = w.get("marketState")
        base_weight = w.get("baseWeight")

        if not all([agent_name, market_state, base_weight]):
            continue

        session.execute(
            text("UPDATE agent_weights SET base_weight = :bw, "
                 "effective_weight = :bw * calib_factor, updated_at = NOW() "
                 "WHERE agent_name = :name AND market_state = :ms"),
            {"bw": base_weight, "name": agent_name, "ms": market_state},
        )

    # 检查同一 market_state 下权重和是否为 1.0
    for ms in ["mainline_confirmed", "oscillating"]:
        row = session.execute(
            text("SELECT SUM(base_weight) FROM agent_weights WHERE market_state = :ms"),
            {"ms": ms},
        ).scalar() or 0
        if abs(float(row) - 1.0) > 0.01:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail=f"权重配置不合法: market_state={ms} 的 base_weight 总和={row:.2f}，必须=1.0",
            )

    session.commit()

    return {
        "code": 0,
        "message": "success",
        "data": None,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/trigger")
def trigger_analysis(
    body: dict[str, Any],
    session: Session = Depends(_get_sync_session),
):
    """手动触发Agent分析 [DD-04 3.6节]"""
    stock_codes = body.get("stockCodes")
    dt = date.today().isoformat()

    orchestrator = _create_orchestrator(session)
    decisions = orchestrator.run_daily_analysis(
        analysis_date=dt,
        stock_codes=stock_codes,
    )

    return {
        "code": 0,
        "message": "Agent分析完成",
        "data": {
            "taskId": f"agent_{dt.replace('-', '')}_001",
            "status": "completed",
            "stockCount": len(decisions),
            "decisions": [
                {"stockCode": d.stock_code, "decision": d.decision.value, "totalScore": d.total_score}
                for d in decisions
            ],
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/calibration")
def query_calibration(
    session: Session = Depends(_get_sync_session),
):
    """查询校准面板数据 [DD-04 3.7节]"""
    # 获取所有 Agent 的最新统计
    rows = session.execute(
        text("SELECT DISTINCT agent_name FROM agent_weights ORDER BY agent_name"),
    ).fetchall()

    agents = []
    for (agent_name,) in rows:
        # 获取该 Agent 的历史成绩
        history_rows = session.execute(
            text("SELECT date, predicted_outcome, actual_outcome "
                 "FROM agent_discussions WHERE agent_name = :name "
                 "AND actual_outcome IS NOT NULL "
                 "ORDER BY date DESC LIMIT 20"),
            {"name": agent_name},
        ).fetchall()

        # 获取权重信息
        weight_row = session.execute(
            text("SELECT calib_factor, win_rate, recent_count "
                 "FROM agent_weights WHERE agent_name = :name LIMIT 1"),
            {"name": agent_name},
        ).fetchone()

        history = []
        win_rate_trend = []
        for h in history_rows:
            history.append({
                "date": h[0].isoformat() if hasattr(h[0], 'isoformat') else str(h[0]),
                "predicted": h[1],
                "actual": h[2],
            })

        display_names = {
            "mainline_hunter": "主线猎手",
            "fund_detective": "资金侦探",
            "sentiment_catcher": "情绪捕手",
            "experience_judge": "经验法官",
        }

        agents.append({
            "agentName": agent_name,
            "displayName": display_names.get(agent_name, agent_name),
            "winRate": float(weight_row[1]) if weight_row and weight_row[1] else 0.5,
            "recentCount": weight_row[2] if weight_row else 0,
            "calibFactor": float(weight_row[0]) if weight_row and weight_row[0] else 1.0,
            "history": history,
            "winRateTrend": win_rate_trend,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {"agents": agents},
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/llm-usage")
def query_llm_usage(
    start_date: str | None = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期(YYYY-MM-DD)"),
    group_by: str = Query("day", regex="^(day|agent|model)$"),
    session: Session = Depends(_get_sync_session),
):
    """查询LLM用量统计 [DD-04 3.8节]"""
    from datetime import timedelta

    end = end_date or date.today().isoformat()
    start = start_date or (date.today() - timedelta(days=7)).isoformat()

    if group_by == "day":
        rows = session.execute(
            text("SELECT date, SUM(prompt_tokens), SUM(completion_tokens), "
                 "SUM(total_cost), SUM(call_count) "
                 "FROM llm_usage WHERE date >= :start AND date <= :end "
                 "GROUP BY date ORDER BY date DESC"),
            {"start": start, "end": end},
        ).fetchall()
        daily_usage = [
            {
                "date": str(r[0]) if r[0] else None,
                "totalPromptTokens": r[1] or 0,
                "totalCompletionTokens": r[2] or 0,
                "totalCost": float(r[3]) if r[3] else 0,
                "callCount": r[4] or 0,
            }
            for r in rows
        ]
    elif group_by == "agent":
        rows = session.execute(
            text("SELECT agent_name, SUM(prompt_tokens), SUM(completion_tokens), "
                 "SUM(total_cost), SUM(call_count) "
                 "FROM llm_usage WHERE date >= :start AND date <= :end "
                 "GROUP BY agent_name ORDER BY SUM(total_cost) DESC"),
            {"start": start, "end": end},
        ).fetchall()
        daily_usage = [
            {
                "agentName": r[0] or "unknown",
                "totalPromptTokens": r[1] or 0,
                "totalCompletionTokens": r[2] or 0,
                "totalCost": float(r[3]) if r[3] else 0,
                "callCount": r[4] or 0,
            }
            for r in rows
        ]
    else:
        rows = session.execute(
            text("SELECT model, SUM(prompt_tokens), SUM(completion_tokens), "
                 "SUM(total_cost), SUM(call_count) "
                 "FROM llm_usage WHERE date >= :start AND date <= :end "
                 "GROUP BY model ORDER BY SUM(total_cost) DESC"),
            {"start": start, "end": end},
        ).fetchall()
        daily_usage = [
            {
                "model": r[0] or "unknown",
                "totalPromptTokens": r[1] or 0,
                "totalCompletionTokens": r[2] or 0,
                "totalCost": float(r[3]) if r[3] else 0,
                "callCount": r[4] or 0,
            }
            for r in rows
        ]

    budget_status = get_budget_status()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "dailyUsage": daily_usage,
            "budgetStatus": budget_status,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/llm-budget")
def update_llm_budget(
    body: dict[str, Any],
):
    """设置Token预算"""
    # TODO: 持久化预算配置到数据库
    return {
        "code": 0,
        "message": "预算配置已更新（当前为内存模式）",
        "data": body,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/prompts")
def query_prompts(
    session: Session = Depends(_get_sync_session),
):
    """查询提示词列表"""
    rows = session.execute(
        text("SELECT id, agent_name, version, is_active, change_note, created_at "
             "FROM agent_prompts ORDER BY agent_name, version DESC"),
    ).fetchall()

    prompts = [
        {
            "id": r[0],
            "agentName": r[1],
            "version": r[2],
            "isActive": r[3],
            "changeNote": r[4],
            "createdAt": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {"prompts": prompts},
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/prompts/{prompt_id}/activate")
def activate_prompt(
    prompt_id: int,
    session: Session = Depends(_get_sync_session),
):
    """激活提示词版本"""
    # 检查版本是否存在
    prompt = session.execute(
        text("SELECT id, agent_name FROM agent_prompts WHERE id = :id"),
        {"id": prompt_id},
    ).fetchone()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词版本不存在")

    agent_name = prompt[1]

    # 先取消该 Agent 所有版本的激活状态
    session.execute(
        text("UPDATE agent_prompts SET is_active = FALSE WHERE agent_name = :name"),
        {"name": agent_name},
    )

    # 激活目标版本
    session.execute(
        text("UPDATE agent_prompts SET is_active = TRUE WHERE id = :id"),
        {"id": prompt_id},
    )

    session.commit()

    return {
        "code": 0,
        "message": f"{agent_name} 版本 {prompt_id} 已激活",
        "data": None,
        "timestamp": datetime.now().isoformat(),
    }
