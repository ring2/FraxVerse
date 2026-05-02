"""
FraxVerse · LIVE 模式交易代理

当交易模式切换到 LIVE 时，TradeEngine 通过此 Broker 将订单转发到
quant-qmt-proxy（运行在 Windows 机器上），后者调用 miniQMT 实际下单。

架构：
    FraXVerse Linux Server  --HTTP-->  quant-qmt-proxy (Windows)  --xtquant-->  miniQMT

集成点：
    1. OrderExecutor.execute_order() 在 LIVE 模式下调用 QmtLiveBroker.submit()
    2. LIVE 模式不模拟成交，而是等待 proxy 返回真实成交结果
    3. 支持同步查询资产、持仓、订单状态
"""

import time
from decimal import Decimal
from typing import Any

from src.execution.qmt_proxy_client import (
    QmtAccountInfo,
    QmtOrderResult,
    QmtPosition,
    QmtProxyClient,
    QmtProxyError,
    QmtSessionInfo,
    stock_code_to_qmt,
)


class QmtLiveBroker:
    """
    LIVE 模式代理 — 对接 quant-qmt-proxy

    管理 quant-qmt-proxy 的会话生命周期：
    1. start() — 打开会话
    2. submit_order() — 提交真实订单
    3. get_asset() / get_positions() — 查询真实资产/持仓
    4. close() — 关闭会话
    """

    def __init__(
        self,
        proxy_url: str = "http://127.0.0.1:8000",
        api_key: str | None = None,
        account_id: str = "",
        account_type: str = "STOCK",
        timeout: float = 30.0,
        auto_reconnect: bool = True,
        max_retries: int = 3,
    ):
        self.proxy_url = proxy_url
        self.api_key = api_key
        self.account_id = account_id
        self.account_type = account_type
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self.max_retries = max_retries

        # 运行时状态
        self._client: QmtProxyClient | None = None
        self._session: QmtSessionInfo | None = None
        self._is_started = False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @property
    def is_started(self) -> bool:
        """是否已启动并打开会话"""
        return self._is_started and self._session is not None

    def start(self) -> QmtSessionInfo:
        """
        启动 broker：创建 HTTP 客户端 + 打开交易会话

        会重试 max_retries 次。
        """
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._client = QmtProxyClient(
                    base_url=self.proxy_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )

                # 先检查服务是否存活
                if not self._client.health():
                    raise QmtProxyError(
                        f"quant-qmt-proxy 服务不可达 ({self.proxy_url})",
                    )

                # 打开交易会话
                self._session = self._client.open_session(
                    account_id=self.account_id,
                    account_type=self.account_type,
                )

                if not self._session.orders_enabled:
                    # 注意：mock 模式下也允许下单
                    pass  # 生产环境可加日志

                self._is_started = True
                return self._session

            except QmtProxyError:
                raise  # 直接抛出不重试
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 指数退避
                self._cleanup()

        raise QmtProxyError(
            f"启动 LIVE Broker 失败（已重试 {self.max_retries} 次）: {last_error}",
        )

    def close(self):
        """
        关闭 broker：关闭会话 + 清理 HTTP 客户端
        """
        close_error = None
        if self._client and self._session:
            try:
                self._client.close_session(self._session.session_id)
            except Exception as exc:
                close_error = exc

        self._cleanup()
        self._is_started = False
        self._session = None

        if close_error:
            raise QmtProxyError(f"关闭会话时出错: {close_error}")

    def _cleanup(self):
        """清理 HTTP 客户端资源"""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _ensure_started(self):
        """确保 broker 已启动，否则自动重连或报错"""
        if self.is_started:
            return

        if not self.auto_reconnect:
            raise QmtProxyError("LIVE Broker 未启动，请先调用 start()")

        # 自动重连
        try:
            self.start()
        except Exception as exc:
            raise QmtProxyError(
                f"LIVE Broker 自动重连失败: {exc}",
            ) from exc

    def _get_client(self) -> QmtProxyClient:
        """获取客户端（确保已启动）"""
        self._ensure_started()
        assert self._client is not None
        return self._client

    def _get_session_id(self) -> str:
        """获取会话ID（确保已启动）"""
        self._ensure_started()
        assert self._session is not None
        return self._session.session_id

    # ------------------------------------------------------------------
    # 下单
    # ------------------------------------------------------------------

    def submit_order(
        self,
        stock_code: str,
        direction: str,  # buy / sell
        volume: int,
        price_type: int = 2,  # 1=限价, 2=市价
        price: float = 0.0,
        strategy_name: str = "",
        order_remark: str = "",
    ) -> dict[str, Any]:
        """
        提交订单到 quant-qmt-proxy

        Returns:
            {
                "order_id": str,
                "status_code": int,
                "status_msg": str,
                "traded_volume": int,
                "traded_price": float,
                "raw": QmtOrderResult,
            }

        Raises:
            QmtProxyError: 下单失败
        """
        client = self._get_client()
        session_id = self._get_session_id()

        side = "BUY" if direction.lower() == "buy" else "SELL"
        qmt_code = stock_code_to_qmt(stock_code)

        result: QmtOrderResult = client.submit_order(
            session_id=session_id,
            stock_code=qmt_code,
            side=side,
            volume=volume,
            price_type=price_type,
            price=price,
            strategy_name=strategy_name,
            order_remark=order_remark,
        )

        # 判断是否成功（50=已提交, 55=已成交都算成功提交）
        is_ok = result.status_code in (50, 55) or "成功" in result.status_msg
        if not is_ok:
            raise QmtProxyError(
                f"下单被拒绝: [{result.status_code}] {result.status_msg}",
                api_code=result.status_code,
                api_message=result.status_msg,
            )

        return {
            "order_id": result.order_id,
            "stock_code": qmt_code,
            "direction": direction,
            "volume": int(result.volume),
            "price": float(result.price),
            "price_type": result.price_type,
            "status_code": result.status_code,
            "status_msg": result.status_msg,
            "traded_volume": int(result.traded_volume),
            "traded_price": float(result.traded_price),
        }

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        client = self._get_client()
        session_id = self._get_session_id()
        return client.cancel_order(session_id, order_id)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_asset(self) -> dict[str, float]:
        """查询真实资产信息"""
        client = self._get_client()
        session_id = self._get_session_id()
        asset: QmtAccountInfo = client.get_asset(session_id)
        return {
            "total_asset": asset.total_asset,
            "cash": asset.cash,
            "frozen_cash": asset.frozen_cash,
            "market_value": asset.market_value,
            "available_cash": asset.available_cash,
        }

    def get_positions(self) -> list[dict[str, Any]]:
        """查询真实持仓列表"""
        client = self._get_client()
        session_id = self._get_session_id()
        positions: list[QmtPosition] = client.get_positions(session_id)

        result = []
        for p in positions:
            result.append({
                "stock_code": p.stock_code,
                "volume": p.volume,
                "available_volume": p.available_volume,
                "cost_price": round(p.cost_price, 3),
                "market_price": round(p.market_price, 2),
                "market_value": round(p.market_value, 2),
                "profit_loss": round(p.profit_loss, 2),
                "profit_loss_ratio": round(p.profit_loss_ratio * 100, 2),
            })
        return result

    def get_orders(
        self, cancelable_only: bool = False,
    ) -> list[dict[str, Any]]:
        """查询真实订单列表"""
        client = self._get_client()
        session_id = self._get_session_id()
        return client.get_orders(session_id, cancelable_only=cancelable_only)

    def get_trades(self) -> list[dict[str, Any]]:
        """查询真实成交列表"""
        client = self._get_client()
        session_id = self._get_session_id()
        return client.get_trades(session_id)

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------

    def is_proxy_alive(self) -> bool:
        """检查 quant-qmt-proxy 是否存活"""
        if not self._client:
            return False
        try:
            return self._client.health()
        except Exception:
            return False
