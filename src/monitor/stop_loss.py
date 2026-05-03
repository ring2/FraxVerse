"""
FraxVerse · 止损监视器（独立进程）

定时扫描持仓 → 检查止损条件 → 自动卖出 → 记录风险事件 → 微信通知
"""
import logging
import signal
import time
from datetime import date
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models import (
    DailyKlines,
    Positions,
    RiskEvents,
    StopLossConditions,
    TradeMode,
)
from src.db.session import get_session
from src.execution.engine import TradeEngine

logger = logging.getLogger(__name__)

# 默认扫描间隔（秒）
DEFAULT_SCAN_INTERVAL = 30


class StopLossMonitor:
    """
    止损监视器

    运行逻辑：
    1. 每 N 秒扫描一次所有持仓
    2. 检查每个持仓的止损条件
    3. 满足条件 → 自动卖出 → 记录风险事件
    """

    def __init__(self, scan_interval: int = DEFAULT_SCAN_INTERVAL):
        self.scan_interval = scan_interval
        self._running = False

    def start(self):
        """启动监视器"""
        self._running = True
        logger.info(f"止损监视器启动 (间隔 {self.scan_interval}s)")

        try:
            # 优雅退出
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)
        except ValueError:
            # 非主线程不支持 signal，忽略
            pass

        while self._running:
            try:
                self._scan_cycle()
            except Exception as e:
                logger.error(f"扫描周期异常: {e}", exc_info=True)
            time.sleep(self.scan_interval)

        logger.info("止损监视器已停止")

    def stop(self):
        """停止监视器"""
        self._running = False

    def _handle_signal(self, signum, frame):
        logger.info(f"收到信号 {signum}，准备停止...")
        self.stop()

    def _scan_cycle(self):
        """执行一次扫描周期"""
        with get_session() as db:
            # 检查交易模式
            trade_mode = db.execute(
                select(TradeMode).limit(1)
            ).scalar_one_or_none()

            if not trade_mode or trade_mode.emergency_stop:
                return  # 紧急停止或未初始化，跳过

            # 获取所有持仓
            positions = db.execute(
                select(Positions).where(Positions.total_volume > 0)
            ).scalars().all()

            if not positions:
                return

            logger.debug(f"扫描 {len(positions)} 个持仓")

            for pos in positions:
                self._check_position(db, pos)

    def _check_position(self, db: Session, pos: Positions):
        """检查单个持仓的止损条件"""
        # 获取止损条件
        sl_cond = db.execute(
            select(StopLossConditions).where(
                StopLossConditions.position_id == pos.id,
                StopLossConditions.is_active,
            )
        ).scalar_one_or_none()

        if not sl_cond:
            return  # 无止损条件

        # 获取当前价格（从最新日K）
        latest_kline = db.execute(
            select(DailyKlines)
            .where(DailyKlines.stock_code == pos.stock_code)
            .order_by(desc(DailyKlines.trade_date))
            .limit(1)
        ).scalar_one_or_none()

        if not latest_kline:
            return

        current_price = Decimal(str(latest_kline.close))
        cost_price = Decimal(str(pos.cost_price))
        pnl_pct = (current_price - cost_price) / cost_price * 100

        # 检查止损条件
        triggered = False
        trigger_reason = ""

        # 1. 固定止损价
        if sl_cond.stop_loss_price and current_price <= Decimal(str(sl_cond.stop_loss_price)):
            triggered = True
            trigger_reason = f"触及止损价 {sl_cond.stop_loss_price}"

        # 2. 浮亏百分比止损
        if sl_cond.max_loss_pct and pnl_pct <= -Decimal(str(sl_cond.max_loss_pct)):
            triggered = True
            trigger_reason = f"浮亏超过 {sl_cond.max_loss_pct}%"

        # 3. 最大损失金额
        if sl_cond.max_loss_amount:
            loss_amount = (current_price - cost_price) * Decimal(str(pos.total_volume))
            if loss_amount <= -Decimal(str(sl_cond.max_loss_amount)):
                triggered = True
                trigger_reason = f"损失超过 {sl_cond.max_loss_amount}"

        if triggered:
            self._execute_stop_loss(db, pos, sl_cond, current_price, pnl_pct, trigger_reason)

    def _execute_stop_loss(
        self,
        db: Session,
        pos: Positions,
        sl_cond: StopLossConditions,
        current_price: Decimal,
        pnl_pct: Decimal,
        reason: str,
    ):
        """执行止损卖出"""
        available = pos.available_volume
        if available <= 0:
            logger.warning(f"持仓 {pos.id} 可用数量为0，跳过")
            return

        logger.warning(
            f"触发止损: stock_code={pos.stock_code} | "
            f"原因={reason} | 价格={current_price} | 浮盈={pnl_pct:.2f}%"
        )

        # 执行卖出
        engine = TradeEngine(db)
        order = engine.sell(
            stock_code=pos.stock_code,
            volume=available,
            price=current_price,
            reason=f"止损触发: {reason}",
        )

        # 记录风险事件
        risk_event = RiskEvents(
            event_type="STOP_LOSS_TRIGGERED",
            event_level="HIGH",
            trigger_value=float(pnl_pct),
            threshold_value=float(-Decimal(str(sl_cond.max_loss_pct))),
            trigger_reason=reason,
            action_taken="auto_sell",
            action_detail={
                "trigger_price": float(current_price),
                "cost_price": float(pos.cost_price),
                "pnl_pct": float(pnl_pct),
                "quantity": available,
                "order_id": order.id,
            },
            trade_date=date.today(),
        )
        db.add(risk_event)
        db.commit()

        logger.info(f"止损执行完成: 订单 {order.id}")

    def check_single(self, position_id: int) -> dict:
        """手动检查单个持仓（供API调用）"""
        with get_session() as db:
            pos = db.get(Positions, position_id)
            if not pos:
                return {"error": "持仓不存在"}

            sl_cond = db.execute(
                select(StopLossConditions).where(
                    StopLossConditions.position_id == pos.id,
                    StopLossConditions.is_active,
                )
            ).scalar_one_or_none()

            if not sl_cond:
                return {"status": "no_stop_loss", "position_id": position_id}

            # 获取最新价格
            latest_kline = db.execute(
                select(DailyKlines)
                .where(DailyKlines.stock_code == pos.stock_code)
                .order_by(desc(DailyKlines.trade_date))
                .limit(1)
            ).scalar_one_or_none()

            if not latest_kline:
                return {"error": "无最新价格数据"}

            current_price = Decimal(str(latest_kline.close))
            cost_price = Decimal(str(pos.cost_price))
            pnl_pct = (current_price - cost_price) / cost_price * 100

            return {
                "position_id": position_id,
                "stock_code": pos.stock_code,
                "current_price": float(current_price),
                "cost_price": float(cost_price),
                "pnl_pct": float(pnl_pct),
                "stop_loss_price": float(sl_cond.stop_loss_price) if sl_cond.stop_loss_price else None,
                "max_loss_pct": float(sl_cond.max_loss_pct) if sl_cond.max_loss_pct else None,
                "max_loss_amount": float(sl_cond.max_loss_amount) if sl_cond.max_loss_amount else None,
                "available_volume": pos.available_volume,
            }


def run_monitor(scan_interval: int = DEFAULT_SCAN_INTERVAL):
    """运行止损监视器"""
    monitor = StopLossMonitor(scan_interval=scan_interval)
    monitor.start()

# 集成微信推送
try:
    from src.notification.wechat import get_notifier

    def _notify_stop_loss(stock_code, trigger_price, cost_price, pnl_pct, reason):
        """止损推送通知"""
        notifier = get_notifier()
        notifier.send_stop_loss_alert(
            stock_code=stock_code,
            trigger_price=Decimal(str(trigger_price)),
            cost_price=Decimal(str(cost_price)),
            pnl_pct=Decimal(str(pnl_pct)),
            reason=reason,
        )
except ImportError:
    _notify_stop_loss = None
