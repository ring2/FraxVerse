"""交易路由 — /api/v1/trade/*"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.models import Positions, StockPool, TradeMode, TradeOrders
from src.db.session import get_session
from src.schemas.trade import (
    OrderCreateRequest,
    OrderResponse,
    PositionItem,
    StockPoolItem,
    TradeModeResponse,
    TradeModeUpdateRequest,
)

router = APIRouter(prefix="/api/v1/trade", tags=["trade"])


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询交易订单列表"""
    q = db.query(TradeOrders).order_by(TradeOrders.created_at.desc())
    if status_filter:
        q = q.filter(TradeOrders.status == status_filter)
    return q.limit(limit).all()


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """查询单笔订单"""
    order = db.query(TradeOrders).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/orders", response_model=OrderResponse)
def create_order(
    req: OrderCreateRequest,
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """创建订单（SIMULATION模式直接标记完成）"""
    import uuid

    from src.db.models import TradeMode as TradeModeModel

    mode = db.query(TradeModeModel).first()
    current_mode = mode.current_mode if mode else "SIMULATION"

    order = TradeOrders(
        client_order_id=str(uuid.uuid4()),
        stock_code=req.stock_code,
        direction=req.direction,
        order_type=req.order_type,
        price=req.price,
        volume=req.volume,
        filled_volume=req.volume if current_mode == "SIMULATION" else 0,
        filled_amount=(req.price * req.volume) if (current_mode == "SIMULATION" and req.price) else 0,
        status="filled" if current_mode == "SIMULATION" else "pending",
        trigger_source="manual",
        trade_mode=current_mode,
        strategy_type=req.strategy_type,
        reason=req.reason,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """撤销订单"""
    order = db.query(TradeOrders).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status in ("filled", "cancelled"):
        raise HTTPException(status_code=400, detail=f"订单状态 {order.status}，无法撤销")
    order.status = "cancelled"
    db.commit()
    return {"message": "已撤销"}


@router.get("/positions", response_model=list[PositionItem])
def list_positions(
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询当前持仓"""
    positions = db.query(Positions).filter(Positions.total_volume > 0).all()
    result = []
    for p in positions:
        from src.db.models import Stocks
        stock = db.query(Stocks).filter_by(code=p.stock_code).first()
        result.append(PositionItem(
            stock_code=p.stock_code,
            stock_name=stock.name if stock else None,
            total_volume=p.total_volume,
            available_volume=p.available_volume,
            cost_price=p.cost_price,
            market_value=p.market_value,
            unrealized_pnl=p.unrealized_pnl,
            unrealized_pnl_pct=p.unrealized_pnl_pct,
            position_pct=p.position_pct,
            entry_date=p.entry_date,
        ))
    return result


@router.get("/pool", response_model=list[StockPoolItem])
def get_stock_pool(
    pool_date: date | None = None,
    strategy: str | None = Query(None, alias="strategy"),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """查询每日股票池"""
    q = db.query(StockPool).order_by(StockPool.date.desc())
    if pool_date:
        q = q.filter(StockPool.date == pool_date)
    if strategy:
        q = q.filter(StockPool.strategy_type == strategy)
    return q.limit(100).all()


@router.get("/mode", response_model=TradeModeResponse)
def get_trade_mode(db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """查询交易模式"""
    mode = db.query(TradeMode).first()
    if not mode:
        return TradeModeResponse(current_mode="SIMULATION", confirm_mode="advisory", emergency_stop=False)
    return TradeModeResponse(
        current_mode=mode.current_mode,
        confirm_mode=mode.confirm_mode,
        emergency_stop=mode.emergency_stop,
    )


@router.post("/mode")
def update_trade_mode(
    req: TradeModeUpdateRequest,
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """切换交易模式"""
    mode = db.query(TradeMode).first()
    if not mode:
        raise HTTPException(status_code=500, detail="trade_mode 表未初始化")
    if req.target_mode:
        mode.current_mode = req.target_mode
    if req.confirm_mode:
        mode.confirm_mode = req.confirm_mode
    mode.updated_at = datetime.now()
    db.commit()
    parts = []
    if req.target_mode:
        parts.append(f"交易模式={req.target_mode}")
    if req.confirm_mode:
        parts.append(f"确认模式={req.confirm_mode}")
    return {"message": "已更新: " + ", ".join(parts)}


@router.post("/emergency-stop")
def emergency_stop(db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """紧急停止"""
    mode = db.query(TradeMode).first()
    if not mode:
        raise HTTPException(status_code=500, detail="trade_mode 表未初始化")
    mode.emergency_stop = True
    mode.emergency_stopped_at = datetime.now()
    db.commit()
    return {"message": "紧急停止已触发"}
