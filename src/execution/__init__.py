"""
FraxVerse · 交易执行模块包

模块组件：
- engine: OrderExecutor, PositionManager, StopProfitManager, TradeEngine
- qmt_proxy_client: quant-qmt-proxy HTTP 客户端
- live_broker: QmtLiveBroker（LIVE 模式代理）
"""
from src.execution.engine import (
    CooldownError,
    DuplicateOrderError,
    EmergencyStopError,
    FlatAverageForbiddenError,
    ModeNotAllowedError,
    NoStockError,
    OrderExecutor,
    PositionManager,
    StopProfitManager,
    TradeEngine,
    TradeError,
)
from src.execution.live_broker import QmtLiveBroker
from src.execution.qmt_proxy_client import QmtProxyClient, QmtProxyError
