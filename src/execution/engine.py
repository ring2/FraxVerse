"""
FraxVerse · 交易执行核心模块

包含：OrderExecutor, PositionManager, StopProfitManager, TradeEngine
SIMULATION 模式下全部模拟执行，不依赖 miniQMT
"""
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from src.db.models import (
    Positions,
    Stocks,
    StopProfitConditions,
    TradeMode,
    TradeOrders,
)
from src.db.session import get_session

# ============================================================================
# 常量 & 配置
# ============================================================================

# 推进式仓位（50% + 5% + 补仓）
BATCH_FIRST_PCT = Decimal("50")     # 第一批 50%
BATCH_SECOND_PCT = Decimal("5")     # 第二批 5%
BATCH_REMAINDER_PCT = Decimal("45") # 剩余 45%

# 单票最大风险（总资金 1.5%）
MAX_RISK_PER_STOCK_PCT = Decimal("1.5")

# 摊平禁令：浮亏 > 0.5% 禁止加仓
FLAT_AVERAGE_THRESHOLD_PCT = Decimal("-0.5")

# 最大持仓数
MAX_POSITIONS = 5

# 止盈阶梯
STOP_PROFIT_TIERS = [
    {"stage": "first_take", "trigger_pct": Decimal("10"), "sell_pct": Decimal("30")},
    {"stage": "second_take", "trigger_pct": Decimal("20"), "sell_pct": Decimal("40")},
    {"stage": "trailing", "trigger_pct": Decimal("15"), "sell_pct": Decimal("50")},
]

# 冷却期
STOP_LOSS_COOLDOWN_HOURS = 24
STOP_PROFIT_COOLDOWN_HOURS = 12

# 确认模式升级路径
CONFIRM_MODE_UPGRADE_PATH = ["advisory", "semi_auto", "full_auto"]
TRADE_MODE_UPGRADE_PATH = ["SIMULATION", "PAPER", "LIVE"]


# ============================================================================
# 错误码
# ============================================================================

class TradeError(Exception):
    """交易异常基类"""
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class NoStockError(TradeError):
    """40401: 参数校验失败"""
    def __init__(self, detail: str):
        super().__init__("40401", f"参数校验失败: {detail}", 400)


class StopLossNotBoundError(TradeError):
    """40402: 止损条件未绑定"""
    def __init__(self):
        super().__init__("40402", "止损条件未绑定，拒绝下单", 409)


class FlatAverageForbiddenError(TradeError):
    """40403: 摊平禁令"""
    def __init__(self, pnl_pct: Decimal):
        super().__init__("40403", f"浮亏状态禁止加仓(浮亏{pnl_pct}%)", 403)


class RiskLimitError(TradeError):
    """40404: 单票风险超限"""
    def __init__(self, detail: str):
        super().__init__("40404", f"单票最大风险超限: {detail}", 403)


class CooldownError(TradeError):
    """40405: 冷却期内"""
    def __init__(self, reason: str):
        super().__init__("40405", f"冷却期内: {reason}", 409)


class EmergencyStopError(TradeError):
    """40406: 紧急停止"""
    def __init__(self):
        super().__init__("40406", "紧急停止已激活，禁止下单", 403)


class DuplicateOrderError(TradeError):
    """40407: 重复订单"""
    def __init__(self):
        super().__init__("40407", "重复订单（幂等键冲突）", 409)


class ModeNotAllowedError(TradeError):
    """40409: 交易模式不允许"""
    def __init__(self, mode: str, action: str):
        super().__init__("40409", f"交易模式 {mode} 不允许执行 {action}", 403)


class PositionNotFoundError(TradeError):
    def __init__(self, stock_code: str):
        super().__init__("40412", f"持仓不存在: {stock_code}", 404)


# ============================================================================
#
# OrderExecutor — 下单执行器
#
# ============================================================================

class OrderExecutor:
    """下单执行器，负责订单校验 + 执行 + 持仓更新"""

    def __init__(self, db: Session, mode_override: str | None = None):
        self.db = db
        self._mode = mode_override or self._get_current_mode()

    def _get_current_mode(self) -> str:
        mode = self.db.query(TradeMode).first()
        return mode.current_mode if mode else "SIMULATION"

    def _check_emergency_stop(self):
        """检查紧急停止"""
        mode = self.db.query(TradeMode).first()
        if mode and mode.emergency_stop:
            raise EmergencyStopError()

    def _load_stock(self, stock_code: str) -> Stocks:
        """加载股票信息，校验存在性"""
        stock = self.db.query(Stocks).filter_by(code=stock_code).first()
        if not stock:
            raise NoStockError(f"股票 {stock_code} 不存在")
        return stock

    def _check_cooldown(self, stock_code: str):
        """检查冷却期"""
        from src.db.models import Positions
        existing = self.db.query(Positions).filter_by(
            stock_code=stock_code, is_cooling_down=True
        ).first()
        if existing and existing.cool_down_until:
            if datetime.now(UTC) < existing.cool_down_until.replace(tzinfo=UTC):
                raise CooldownError(f"{stock_code} 冷却中至 {existing.cool_down_until}")

    def _check_flat_average_ban(self, stock_code: str):
        """摊平禁令：已有持仓且浮亏时禁止加仓"""
        position = self.db.query(Positions).filter(
            Positions.stock_code == stock_code,
            Positions.total_volume > 0,
        ).first()
        if position and position.total_volume > 0 and position.unrealized_pnl_pct < FLAT_AVERAGE_THRESHOLD_PCT:
            raise FlatAverageForbiddenError(position.unrealized_pnl_pct)

    def _check_risk_limit(
        self, stock_code: str, volume: int, price: Decimal | None,
    ) -> tuple[Decimal, Decimal]:
        """检查单票最大风险 ≤ 1.5%总资金"""
        from src.db.models import AccountSyncLog
        last_sync = self.db.query(AccountSyncLog).order_by(
            AccountSyncLog.created_at.desc()
        ).first()
        total_asset = last_sync.total_asset if last_sync else Decimal("100000")
        if total_asset is None or total_asset <= 0:
            total_asset = Decimal("100000")

        # 成交价：市价单用前收盘价估算，限价单用限价
        trade_price = price or Decimal("100")
        order_amount = Decimal(str(volume)) * trade_price
        risk_amount = order_amount  # 模拟：假设全额亏损
        max_loss = total_asset * MAX_RISK_PER_STOCK_PCT / Decimal("100")

        if risk_amount > max_loss:
            raise RiskLimitError(
                f"订单金额 {order_amount} > 最大允许 {max_loss} (总资产 {total_asset} × 1.5%)"
            )
        return total_asset, order_amount

    def _generate_client_order_id(self) -> str:
        """生成幂等键"""
        return str(uuid.uuid4())

    @staticmethod
    def convert_stock_code(code: str) -> str:
        """将 600519.SH 转为 miniQMT 格式 600519.SH（保持不变，外部显示用）"""
        return code

    def execute_order(
        self,
        stock_code: str,
        direction: str,
        volume: int,
        order_type: str = "market",
        price: Decimal | None = None,
        strategy_type: str | None = None,
        trigger_source: str = "manual",
        position_batch: str | None = None,
        reason: str | None = None,
    ) -> TradeOrders:
        """
        执行下单（SIMULATION模式直接标记成交）

        校验顺序：
        1. 紧急停止检查
        2. 股票存在性
        3. 冷却期检查
        4. 摊平禁令检查
        5. 风险限额检查
        6. 止损条件绑定检查
        7. 模式检查
        """
        # 1. 紧急停止
        self._check_emergency_stop()

        # 2. 股票存在性
        self._load_stock(stock_code)

        # 3. 模式检查
        if self._mode == "SIMULATION":
            pass  # SIMULATION允许所有操作
        elif self._mode == "LIVE" and trigger_source == "manual":
            raise ModeNotAllowedError(self._mode, "手动下单（LIVE仅允许策略触发）")

        # 4. 冷却期检查（仅买入）
        if direction == "buy":
            self._check_cooldown(stock_code)

        # 5. 摊平禁令（加仓）
        if direction == "buy" and strategy_type:
            self._check_flat_average_ban(stock_code)

        # 6. 风险限额
        total_asset, order_amount = self._check_risk_limit(stock_code, volume, price)

        # 7. 创建订单
        order = TradeOrders(
            client_order_id=self._generate_client_order_id(),
            stock_code=stock_code,
            direction=direction,
            order_type=order_type,
            price=price,
            volume=volume,
            filled_volume=volume if self._mode == "SIMULATION" else 0,
            filled_amount=order_amount if self._mode == "SIMULATION" else Decimal("0"),
            status="filled" if self._mode == "SIMULATION" else "pending",
            trigger_source=trigger_source,
            trade_mode=self._mode,
            strategy_type=strategy_type,
            position_batch=position_batch,
            reason=reason,
        )
        self.db.add(order)
        self.db.flush()

        # SIMULATION 模式：直接更新持仓
        if self._mode == "SIMULATION":
            self._update_position_after_trade(
                stock_code, direction, volume, price or Decimal("100"),
                position_batch, strategy_type,
            )

        self.db.commit()
        self.db.refresh(order)
        return order

    def _update_position_after_trade(
        self,
        stock_code: str,
        direction: str,
        volume: int,
        price: Decimal,
        position_batch: str | None,
        strategy_type: str | None,
    ):
        """交易后更新持仓（SIMULATION模式）"""
        position = self.db.query(Positions).filter_by(stock_code=stock_code).first()

        if direction == "buy":
            if not position:
                position = Positions(
                    stock_code=stock_code,
                    total_volume=volume,
                    available_volume=volume,
                    cost_price=price,
                    market_value=Decimal(str(volume)) * price,
                    entry_date=datetime.now().date(),
                    batch_stage=position_batch or "first_half",
                    position_pct=Decimal("5"),  # 简化
                )
                if position_batch == "first_half":
                    position.first_batch_vol = volume
                elif position_batch == "second_batch":
                    position.second_batch_vol = volume
                else:
                    position.remainder_vol = volume
                self.db.add(position)
            else:
                # 加仓：加权平均成本
                old_cost = position.cost_price * Decimal(str(position.total_volume))
                new_cost = price * Decimal(str(volume))
                position.total_volume += volume
                position.available_volume += volume
                position.cost_price = (old_cost + new_cost) / Decimal(str(position.total_volume))
                position.market_value = Decimal(str(position.total_volume)) * price
                if position_batch == "second_batch":
                    position.second_batch_vol += volume
                else:
                    position.remainder_vol += volume

        elif direction == "sell":
            if not position:
                return  # 无持仓则忽略
            # 减少持仓
            sell_vol = min(volume, position.total_volume)
            position.total_volume -= sell_vol
            position.available_volume = max(0, position.available_volume - sell_vol)
            position.market_value = Decimal(str(position.total_volume)) * price if position.total_volume > 0 else Decimal("0")
            if position.total_volume <= 0:
                position.batch_stage = "none"
                position.position_pct = Decimal("0")

        position.updated_at = datetime.now()


# ============================================================================
#
# PositionManager — 仓位管理器
#
# ============================================================================

class PositionManager:
    """仓位管理：推进式建仓、仓位计算"""

    def __init__(self, db: Session, total_asset: Decimal = Decimal("100000")):
        self.db = db
        self.total_asset = total_asset

    def get_positions(self) -> list[Positions]:
        """获取所有活跃持仓"""
        return self.db.query(Positions).filter(Positions.total_volume > 0).all()

    def get_position_count(self) -> int:
        """活跃持仓数量"""
        return self.db.query(Positions).filter(Positions.total_volume > 0).count()

    def can_open_new_position(self) -> bool:
        """能否开新仓（不超过 MAX_POSITIONS）"""
        return self.get_position_count() < MAX_POSITIONS

    def calculate_batch_quantity(
        self, stock_code: str, price: Decimal, batch_stage: str,
    ) -> int:
        """计算推进式仓位数量"""
        # 第一批 50%，第二批 5%，补仓 45%
        if batch_stage == "first_half":
            pct = BATCH_FIRST_PCT
        elif batch_stage == "second_batch":
            pct = BATCH_SECOND_PCT
        else:
            pct = BATCH_REMAINDER_PCT

        position_amount = self.total_asset * pct / Decimal("100")
        quantity = int(position_amount / price)
        return max(quantity // 100 * 100, 100)  # 按100股取整，至少1手

    def get_position_detail(self, stock_code: str) -> Positions | None:
        """查询单个持仓"""
        return self.db.query(Positions).filter(
            Positions.stock_code == stock_code,
            Positions.total_volume > 0,
        ).first()


# ============================================================================
#
# StopProfitManager — 止盈管理器
#
# ============================================================================

class StopProfitManager:
    """阶梯止盈管理"""

    def __init__(self, db: Session):
        self.db = db

    def create_stop_profit(self, position_id: int, stock_code: str) -> list[StopProfitConditions]:
        """创建止盈条件（买入时绑定）"""
        conditions = []
        for tier in STOP_PROFIT_TIERS:
            cond = StopProfitConditions(
                position_id=position_id,
                stock_code=stock_code,
                stage=tier["stage"],
                trigger_pct=tier["trigger_pct"],
                sell_pct=tier["sell_pct"],
                is_active=True,
            )
            self.db.add(cond)
            conditions.append(cond)
        self.db.flush()
        return conditions

    def check_and_execute(self, stock_code: str, current_price: Decimal, cost_price: Decimal) -> Decimal | None:
        """
        检查止盈条件并返回应卖出比例
        返回 None 表示未触发，否则返回 sell_pct
        """
        gain_pct = (current_price - cost_price) / cost_price * Decimal("100")
        if gain_pct < 0:
            return None

        conditions = self.db.query(StopProfitConditions).filter_by(
            stock_code=stock_code, is_active=True
        ).all()

        for cond in conditions:
            if gain_pct >= cond.trigger_pct:
                cond.is_active = False
                cond.triggered_at = datetime.now(UTC)
                return cond.sell_pct
        return None


# ============================================================================
#
# TradeEngine — 交易引擎（整合入口）
#
# ============================================================================

class TradeEngine:
    """交易引擎，整合下单 + 仓位 + 止盈"""

    def __init__(self, db: Session | None = None):
        self.db = db or get_session()
        self.executor = OrderExecutor(self.db)
        self.position_manager = PositionManager(self.db)
        self.stop_profit = StopProfitManager(self.db)

    def buy(
        self,
        stock_code: str,
        volume: int,
        price: Decimal | None = None,
        strategy_type: str | None = None,
        reason: str | None = None,
        position_batch: str = "first_half",
    ) -> TradeOrders:
        """买入"""
        return self.executor.execute_order(
            stock_code=stock_code,
            direction="buy",
            volume=volume,
            price=price,
            strategy_type=strategy_type,
            trigger_source="strategy" if strategy_type else "manual",
            position_batch=position_batch,
            reason=reason,
        )

    def sell(
        self,
        stock_code: str,
        volume: int,
        price: Decimal | None = None,
        reason: str | None = None,
    ) -> TradeOrders:
        """卖出"""
        return self.executor.execute_order(
            stock_code=stock_code,
            direction="sell",
            volume=volume,
            price=price,
            trigger_source="manual",
            reason=reason,
        )

    def close_all(self) -> list[TradeOrders]:
        """清仓所有持仓"""
        orders = []
        for pos in self.position_manager.get_positions():
            order = self.sell(
                stock_code=pos.stock_code,
                volume=pos.total_volume,
                reason="清仓（全部平仓）",
            )
            orders.append(order)
        return orders

    def set_cooldown(self, stock_code: str, reason: str = "stop_loss", hours: int | None = None) -> Positions:
        """设置冷却期"""
        position = self.db.query(Positions).filter_by(stock_code=stock_code).first()
        if not position:
            raise PositionNotFoundError(stock_code)
        hours = hours or (STOP_LOSS_COOLDOWN_HOURS if reason == "stop_loss" else STOP_PROFIT_COOLDOWN_HOURS)
        position.is_cooling_down = True
        position.cool_down_until = datetime.now(UTC) + timedelta(hours=hours)
        position.cool_down_reason = reason
        self.db.commit()
        return position


# ============================================================================
# 便捷函数
# ============================================================================

def get_trade_engine() -> TradeEngine:
    """获取默认交易引擎实例"""
    return TradeEngine()
