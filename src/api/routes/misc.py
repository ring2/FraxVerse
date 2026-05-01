"""策略、Agent、经验、新闻、监控路由"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.models import (
    AgentDiscussions,
    AgentWeights,
    BacktestResults,
    Experiences,
    Notifications,
    RiskEvents,
    RiskMetricsDaily,
    StrategyParams,
)
from src.db.session import get_session
from src.schemas.agent import AgentDiscussionItem, AgentWeightItem
from src.schemas.system import (
    BacktestResultItem,
    ExperienceItem,
    NotificationItem,
    RiskEventItem,
    RiskMetricsItem,
    ServiceStatus,
    SystemResource,
)

# —————— 策略路由 ——————
strategy_router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


@strategy_router.get("/backtest-results", response_model=list[BacktestResultItem])
def list_backtest_results(
    strategy_type: str | None = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询回测结果"""
    q = db.query(BacktestResults).order_by(BacktestResults.created_at.desc())
    if strategy_type:
        q = q.filter(BacktestResults.strategy_type == strategy_type)
    return q.limit(limit).all()


@strategy_router.get("/params")
def get_strategy_params(
    strategy_type: str | None = None,
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询策略参数"""
    q = db.query(StrategyParams)
    if strategy_type:
        q = q.filter(StrategyParams.strategy_type == strategy_type)
    return q.all()


# —————— Agent 路由 ——————
agent_router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@agent_router.get("/discussions", response_model=list[AgentDiscussionItem])
def list_agent_discussions(
    stock_code: str | None = None,
    date_str: date | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询Agent讨论记录"""
    q = db.query(AgentDiscussions).order_by(AgentDiscussions.created_at.desc())
    if stock_code:
        q = q.filter(AgentDiscussions.stock_code == stock_code)
    if date_str:
        q = q.filter(AgentDiscussions.date == date_str)
    return q.limit(limit).all()


@agent_router.get("/weights", response_model=list[AgentWeightItem])
def get_agent_weights(db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """查询Agent权重"""
    weights = db.query(AgentWeights).all()
    return [
        AgentWeightItem(
            agent_name=w.agent_name,
            market_state=w.market_state,
            base_weight=float(w.base_weight),
            effective_weight=float(w.effective_weight),
            win_rate=float(w.win_rate) if w.win_rate else None,
        )
        for w in weights
    ]


# —————— 风险路由 ——————
risk_router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@risk_router.get("/events", response_model=list[RiskEventItem])
def list_risk_events(
    event_level: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询风控事件"""
    q = db.query(RiskEvents).order_by(RiskEvents.created_at.desc())
    if event_level:
        q = q.filter(RiskEvents.event_level == event_level)
    return q.limit(limit).all()


@risk_router.get("/metrics", response_model=list[RiskMetricsItem])
def get_risk_metrics(limit: int = Query(30, le=100), db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """查询风控指标"""
    return db.query(RiskMetricsDaily).order_by(RiskMetricsDaily.trade_date.desc()).limit(limit).all()


# —————— 经验路由 ——————
experience_router = APIRouter(prefix="/api/v1/experience", tags=["experience"])


@experience_router.get("/list", response_model=list[ExperienceItem])
def list_experiences(
    market_state: str | None = None,
    strategy_type: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询经验库"""
    q = db.query(Experiences).filter(not Experiences.is_archived).order_by(Experiences.created_at.desc())
    if market_state:
        q = q.filter(Experiences.market_state == market_state)
    if strategy_type:
        q = q.filter(Experiences.strategy_type == strategy_type)
    return q.limit(limit).all()


# —————— 监控路由 ——————
monitor_router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


@monitor_router.get("/services", response_model=list[ServiceStatus])
def get_service_status(user_id: int = Depends(get_current_user_id)):
    """查询服务状态"""
    import subprocess
    services = []
    # PostgreSQL
    pg = subprocess.run(
        ["docker", "exec", "fraxverse-db", "pg_isready", "-q"],
        capture_output=True, timeout=3,
    )
    services.append(ServiceStatus(service="postgresql", status="healthy" if pg.returncode == 0 else "unhealthy"))
    # Redis
    redis = subprocess.run(
        ["redis-cli", "-h", "localhost", "-p", "6379", "ping"],
        capture_output=True, text=True, timeout=3,
    )
    services.append(ServiceStatus(service="redis", status="healthy" if "PONG" in redis.stdout else "unhealthy"))
    return services


@monitor_router.get("/resources", response_model=SystemResource)
def get_system_resources(user_id: int = Depends(get_current_user_id)):
    """查询系统资源"""
    import psutil
    mem = psutil.virtual_memory()
    return SystemResource(
        cpu_percent=psutil.cpu_percent(interval=0.5),
        memory_percent=mem.percent,
        memory_mb=round(mem.used / 1024 / 1024, 1),
        disk_percent=psutil.disk_usage("/").percent,
    )


# —————— 通知路由 ——————
notification_router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@notification_router.get("/", response_model=list[NotificationItem])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询通知"""
    q = db.query(Notifications).filter_by(user_id=user_id).order_by(Notifications.created_at.desc())
    if unread_only:
        q = q.filter(not Notifications.is_read)
    return q.limit(limit).all()


@notification_router.post("/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """标记通知为已读"""
    n = db.query(Notifications).filter_by(id=notification_id, user_id=user_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    db.commit()
    return {"message": "已标记为已读"}


from fastapi import HTTPException
