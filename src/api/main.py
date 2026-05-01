"""
FraxVerse · FastAPI 主应用入口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.routes.auth import router as auth_router
from src.api.routes.market import router as market_router
from src.api.routes.misc import (
    agent_router,
    experience_router,
    monitor_router,
    notification_router,
    risk_router,
    strategy_router,
)
from src.api.routes.trade import router as trade_router
from src.config import settings
from src.db.models import AccountSyncLog, Positions
from src.db.session import check_db_health, get_session
from src.schemas.system import PortfolioSummary

app = FastAPI(
    title="FraxVerse API",
    description="碎片宇宙智能量化交易系统",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(trade_router)
app.include_router(market_router)
app.include_router(strategy_router)
app.include_router(agent_router)
app.include_router(risk_router)
app.include_router(experience_router)
app.include_router(monitor_router)
app.include_router(notification_router)


@app.get("/api/v1/health")
def health_check():
    """健康检查"""
    db_healthy = check_db_health()
    return {
        "status": "ok" if db_healthy else "degraded",
        "version": settings.APP_VERSION,
        "db": "connected" if db_healthy else "disconnected",
    }


@app.get("/api/v1/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_session)):
    """账户资产概览"""
    positions = db.query(Positions).filter(Positions.total_volume > 0).all()
    last_sync = db.query(AccountSyncLog).order_by(AccountSyncLog.created_at.desc()).first()
    return PortfolioSummary(
        total_asset=last_sync.total_asset if last_sync else None,
        available_cash=last_sync.available_cash if last_sync else None,
        total_position_pct=sum(p.position_pct for p in positions) if positions else 0,
        daily_pnl=last_sync.daily_pnl if last_sync else None,
        unrealized_pnl=sum(p.unrealized_pnl for p in positions) if positions else 0,
        position_count=len(positions),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常捕获"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部错误: {str(exc)}"[:200]},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
