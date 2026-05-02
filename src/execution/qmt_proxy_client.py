"""
FraxVerse · quant-qmt-proxy HTTP 客户端

封装对 quant-qmt-proxy REST API 的调用。
quant-qmt-proxy 运行在 Windows 机器上（内网），通过 HTTP 暴露 miniQMT 的下单/查询能力。

API 规范：https://github.com/liqimore/quant-qmt-proxy
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class QmtAccountInfo:
    """quant-qmt-proxy 返回的资产信息"""
    total_asset: float
    cash: float
    frozen_cash: float
    market_value: float
    available_cash: float


@dataclass
class QmtPosition:
    """quant-qmt-proxy 返回的持仓信息"""
    stock_code: str
    volume: int
    available_volume: int
    cost_price: float
    market_price: float
    market_value: float
    profit_loss: float
    profit_loss_ratio: float


@dataclass
class QmtOrderResult:
    """quant-qmt-proxy 返回的下单结果"""
    order_id: str
    stock_code: str
    side: str  # BUY / SELL
    volume: int
    price: float
    price_type: int
    status_code: int  # 50=submitted, 53=part_filled, 54=cancelled, 55=filled
    status_msg: str
    traded_volume: int
    traded_price: float
    order_time_ms: int


@dataclass
class QmtSessionInfo:
    """quant-qmt-proxy 返回的会话信息"""
    session_id: str
    account_id: str
    mode: str
    is_real: bool
    orders_enabled: bool


# ============================================================================
# HTTP 客户端
# ============================================================================


class QmtProxyClient:
    """
    quant-qmt-proxy HTTP 客户端

    用法：
        client = QmtProxyClient(base_url="http://192.168.1.100:8000", api_key="xxx")
        session = client.open_session("账户号")
        order = client.submit_order(session.session_id, "000001.SZ", "BUY", 100, 1, 10.5)
        asset = client.get_asset(session.session_id)
        positions = client.get_positions(session.session_id)
        client.close_session(session.session_id)
    """

    SIDE_BUY = "BUY"
    SIDE_SELL = "SELL"

    # price_type: 1=限价, 2=市价, 4=最优五档
    PRICE_TYPE_LIMIT = 1
    PRICE_TYPE_MARKET = 2
    PRICE_TYPE_BEST5 = 4

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "FraxVerse/0.1",
        }
        if api_key:
            headers["X-API-Key"] = api_key

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    def open_session(self, account_id: str, account_type: str = "STOCK") -> QmtSessionInfo:
        """创建交易会话，返回会话信息"""
        resp = self._client.post(
            "/api/v1/trading/sessions",
            json={"account_id": account_id, "account_type": account_type},
        )
        data = self._parse_response(resp, "open_session")
        sess = data["data"]
        return QmtSessionInfo(
            session_id=sess["session_id"],
            account_id=sess["account_id"],
            mode=sess.get("mode", ""),
            is_real=sess.get("is_real", False),
            orders_enabled=sess.get("orders_enabled", False),
        )

    def get_session(self, session_id: str) -> QmtSessionInfo:
        """查询会话信息"""
        resp = self._client.get(f"/api/v1/trading/sessions/{session_id}")
        data = self._parse_response(resp, "get_session")
        sess = data["data"]
        return QmtSessionInfo(
            session_id=sess["session_id"],
            account_id=sess["account_id"],
            mode=sess.get("mode", ""),
            is_real=sess.get("is_real", False),
            orders_enabled=sess.get("orders_enabled", False),
        )

    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        resp = self._client.delete(f"/api/v1/trading/sessions/{session_id}")
        data = self._parse_response(resp, "close_session")
        return data["data"].get("success", True)

    # ------------------------------------------------------------------
    # 资产 & 持仓
    # ------------------------------------------------------------------

    def get_asset(self, session_id: str) -> QmtAccountInfo:
        """查询资产信息"""
        resp = self._client.get(f"/api/v1/trading/sessions/{session_id}/asset")
        data = self._parse_response(resp, "get_asset")
        asset = data["data"]
        return QmtAccountInfo(
            total_asset=float(asset.get("total_asset", 0)),
            cash=float(asset.get("cash", 0)),
            frozen_cash=float(asset.get("frozen_cash", 0)),
            market_value=float(asset.get("market_value", 0)),
            available_cash=float(asset.get("available_cash", asset.get("cash", 0))),
        )

    def get_positions(self, session_id: str) -> list[QmtPosition]:
        """查询持仓列表"""
        resp = self._client.get(f"/api/v1/trading/sessions/{session_id}/positions")
        data = self._parse_response(resp, "get_positions")
        items = data.get("data", {}).get("items", [])
        return [
            QmtPosition(
                stock_code=p["stock_code"],
                volume=int(p.get("volume", 0)),
                available_volume=int(p.get("available_volume", p.get("can_use_volume", 0))),
                cost_price=float(p.get("cost_price", p.get("avg_price", 0))),
                market_price=float(p.get("market_price", p.get("last_price", 0))),
                market_value=float(p.get("market_value", 0)),
                profit_loss=float(p.get("profit_loss", 0)),
                profit_loss_ratio=float(p.get("profit_loss_ratio", p.get("profit_rate", 0))),
            )
            for p in items
        ]

    def get_orders(
        self, session_id: str, cancelable_only: bool = False,
    ) -> list[dict[str, Any]]:
        """查询订单列表"""
        params = {"cancelable_only": "true"} if cancelable_only else {}
        resp = self._client.get(
            f"/api/v1/trading/sessions/{session_id}/orders",
            params=params,
        )
        data = self._parse_response(resp, "get_orders")
        return data.get("data", {}).get("items", [])

    def get_trades(self, session_id: str) -> list[dict[str, Any]]:
        """查询成交列表"""
        resp = self._client.get(f"/api/v1/trading/sessions/{session_id}/trades")
        data = self._parse_response(resp, "get_trades")
        return data.get("data", {}).get("items", [])

    # ------------------------------------------------------------------
    # 下单 & 撤单
    # ------------------------------------------------------------------

    def submit_order(
        self,
        session_id: str,
        stock_code: str,
        side: str,
        volume: int,
        price_type: int = 2,
        price: float = 0.0,
        strategy_name: str = "",
        order_remark: str = "",
    ) -> QmtOrderResult:
        """
        提交订单

        Args:
            session_id: 交易会话ID
            stock_code: 股票代码（如 000001.SZ）
            side: 方向 BUY / SELL
            volume: 数量（股）
            price_type: 1=限价, 2=市价
            price: 价格（市价单传0）
            strategy_name: 策略名称
            order_remark: 订单备注
        """
        resp = self._client.post(
            f"/api/v1/trading/sessions/{session_id}/orders",
            json={
                "stock_code": stock_code,
                "side": side.upper(),
                "price_type": price_type,
                "volume": volume,
                "price": price,
                "strategy_name": strategy_name,
                "order_remark": order_remark,
            },
        )
        data = self._parse_response(resp, "submit_order")
        order = data["data"]
        return QmtOrderResult(
            order_id=str(order.get("order_id", "")),
            stock_code=str(order.get("stock_code", "")),
            side="BUY" if order.get("order_type") in (23, "23") else "SELL",
            volume=int(order.get("order_volume", 0)),
            price=float(order.get("price", 0.0)),
            price_type=int(order.get("price_type", 2)),
            status_code=int(order.get("order_status_code", 50)),
            status_msg=str(order.get("status_msg", "")),
            traded_volume=int(order.get("traded_volume", 0)),
            traded_price=float(order.get("traded_price", 0.0)),
            order_time_ms=int(order.get("order_time_ms", 0)),
        )

    def cancel_order(
        self,
        session_id: str,
        order_id: str,
    ) -> bool:
        """撤销订单"""
        resp = self._client.post(
            f"/api/v1/trading/sessions/{session_id}/cancel",
            json={"order_id": order_id},
        )
        data = self._parse_response(resp, "cancel_order")
        return data["data"].get("success", False)

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------

    def health(self) -> bool:
        """检查 proxy 是否存活"""
        try:
            resp = self._client.get("/health/")
            return resp.status_code == 200
        except Exception:
            return False

    def health_live(self) -> bool:
        """检查 proxy 的存活探针"""
        try:
            resp = self._client.get("/health/live")
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(resp: httpx.Response, context: str) -> dict[str, Any]:
        """解析 proxy 的标准响应格式 {success, message, code, data}"""
        try:
            data = resp.json()
        except Exception as exc:
            raise QmtProxyError(
                f"[{context}] 响应解析失败: {exc}, status={resp.status_code}",
            ) from exc

        if resp.status_code >= 400 or not data.get("success", False):
            msg = data.get("message", "")
            code = data.get("code", resp.status_code)
            raise QmtProxyError(
                f"[{context}] API 错误 ({code}): {msg}",
                status_code=resp.status_code,
                api_code=code,
                api_message=msg,
            )

        return data

    def close(self):
        """关闭 HTTP 客户端"""
        self._client.close()


# ============================================================================
# 异常
# ============================================================================


class QmtProxyError(Exception):
    """quant-qmt-proxy 调用异常"""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        api_code: int | None = None,
        api_message: str = "",
    ):
        self.status_code = status_code
        self.api_code = api_code
        self.api_message = api_message
        super().__init__(message)


def stock_code_to_qmt(code: str) -> str:
    """
    标准化股票代码为 quant-qmt-proxy 格式

    FraXVerse 内部可能用 600519.SH 或 000001.SZ 格式，
    quant-qmt-proxy 要求统一格式。
    """
    code = code.upper().strip()
    # 如果已有 .SH/.SZ 后缀，保持不变
    if code.endswith(".SH") or code.endswith(".SZ") or code.endswith(".BJ"):
        return code
    # 尝试加后缀（根据纯数字代码前缀判断）
    if code.isdigit():
        if code.startswith("6") or code.startswith("9"):
            return f"{code}.SH"
        elif code.startswith("0") or code.startswith("3") or code.startswith("2"):
            return f"{code}.SZ"
        elif code.startswith("4") or code.startswith("8"):
            return f"{code}.BJ"
    # 无法判断原样返回
    return code
