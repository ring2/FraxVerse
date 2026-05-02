"""
Tests: quant-qmt-proxy HTTP 客户端

覆盖：
1. QmtProxyClient 的会话管理
2. 下单 & 撤单
3. 资产 & 持仓查询
4. 健康检查
5. 错误处理
6. stock_code_to_qmt 工具函数
"""

from unittest.mock import ANY, MagicMock, patch

import httpx
import pytest

from src.execution.qmt_proxy_client import (
    QmtAccountInfo,
    QmtOrderResult,
    QmtPosition,
    QmtProxyClient,
    QmtProxyError,
    QmtSessionInfo,
    stock_code_to_qmt,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_http_client():
    """模拟 httpx.Client"""
    with patch("src.execution.qmt_proxy_client.httpx.Client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def proxy_client(mock_http_client):
    """创建 QmtProxyClient 实例（使用 mock HTTP 客户端）"""
    client = QmtProxyClient(
        base_url="http://localhost:18000",
        api_key="test-api-key-001",
        timeout=0.1,
    )
    # 替换内部 HTTP 客户端为 mock
    client._client = mock_http_client
    return client


# ============================================================================
# Session 管理
# ============================================================================


class TestOpenSession:
    def test_success(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "创建交易会话成功",
            "code": 200,
            "data": {
                "session_id": "session_123456_abc123def",
                "account_id": "88888888",
                "account_type": "STOCK",
                "is_real": False,
                "mode": "mock",
                "environment": "mock",
                "orders_enabled": True,
                "opened_at_ms": 1700000000000,
            },
        }
        mock_http_client.post.return_value = mock_response

        result = proxy_client.open_session("88888888")

        assert isinstance(result, QmtSessionInfo)
        assert result.session_id == "session_123456_abc123def"
        assert result.account_id == "88888888"
        assert result.mode == "mock"
        assert result.is_real is False
        assert result.orders_enabled is True

        mock_http_client.post.assert_called_once_with(
            "/api/v1/trading/sessions",
            json={"account_id": "88888888", "account_type": "STOCK"},
        )

    def test_api_error(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "message": "账户未注册",
            "code": 400,
        }

        mock_http_client.post.return_value = mock_response

        with pytest.raises(QmtProxyError) as exc_info:
            proxy_client.open_session("invalid_account")

        assert "API 错误" in str(exc_info.value)
        assert "账户未注册" in str(exc_info.value)


class TestCloseSession:
    def test_success(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "关闭交易会话成功",
            "code": 200,
            "data": {"success": True},
        }
        mock_http_client.delete.return_value = mock_response

        result = proxy_client.close_session("session_xxx")
        assert result is True

    def test_session_not_found(self, proxy_client, mock_http_client):
        """会话不存在时 close_session 返回 False"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "交易会话不存在",
            "code": 200,
            "data": {"success": False},
        }
        mock_http_client.delete.return_value = mock_response

        result = proxy_client.close_session("session_nonexist")
        assert result is False


# ============================================================================
# 下单
# ============================================================================


class TestSubmitOrder:
    def test_market_order(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "下单成功",
            "code": 200,
            "data": {
                "account_id": "88888888",
                "stock_code": "000001.SZ",
                "instrument_name": "平安银行",
                "order_id": "mock_1001",
                "order_sysid": "",
                "order_time_ms": 1700000000000,
                "order_type": 23,
                "order_volume": 100,
                "price_type": 2,
                "price": 0.0,
                "traded_volume": 0,
                "traded_price": 0.0,
                "order_status_code": 50,
                "status_msg": "submitted",
                "strategy_name": "test_strategy",
                "order_remark": "test_order",
                "direction": "",
                "offset_flag": "",
                "secu_account": "88888888",
            },
        }
        mock_http_client.post.return_value = mock_response

        result = proxy_client.submit_order(
            session_id="session_xxx",
            stock_code="000001.SZ",
            side="BUY",
            volume=100,
            price_type=2,
            strategy_name="test_strategy",
            order_remark="test_order",
        )

        assert isinstance(result, QmtOrderResult)
        assert result.order_id == "mock_1001"
        assert result.stock_code == "000001.SZ"
        assert result.volume == 100
        assert result.status_code == 50
        assert result.status_msg == "submitted"

        mock_http_client.post.assert_called_once_with(
            "/api/v1/trading/sessions/session_xxx/orders",
            json={
                "stock_code": "000001.SZ",
                "side": "BUY",
                "price_type": 2,
                "volume": 100,
                "price": 0.0,
                "strategy_name": "test_strategy",
                "order_remark": "test_order",
            },
        )

    def test_limit_order(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "下单成功",
            "code": 200,
            "data": {
                "account_id": "88888888",
                "stock_code": "600519.SH",
                "order_id": "mock_1002",
                "order_type": 23,
                "order_volume": 100,
                "price_type": 1,
                "price": 1850.0,
                "traded_volume": 100,
                "traded_price": 1850.0,
                "order_status_code": 55,
                "status_msg": "全部成交",
            },
        }
        mock_http_client.post.return_value = mock_response

        result = proxy_client.submit_order(
            session_id="session_xxx",
            stock_code="600519.SH",
            side="BUY",
            volume=100,
            price_type=1,
            price=1850.0,
        )

        assert result.status_code == 55  # 全部成交
        assert result.traded_volume == 100
        assert result.traded_price == 1850.0

    def test_sell_order(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "下单成功",
            "code": 200,
            "data": {
                "order_id": "mock_1003",
                "stock_code": "000001.SZ",
                "order_type": 24,
                "order_volume": 100,
                "order_status_code": 50,
            },
        }
        mock_http_client.post.return_value = mock_response

        result = proxy_client.submit_order(
            session_id="session_xxx",
            stock_code="000001.SZ",
            side="SELL",
            volume=100,
            price_type=2,
        )

        assert result.order_id == "mock_1003"

    def test_cancel_order(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "撤单成功",
            "code": 200,
            "data": {"success": True},
        }
        mock_http_client.post.return_value = mock_response

        result = proxy_client.cancel_order("session_xxx", "mock_1001")
        assert result is True


# ============================================================================
# 资产 & 持仓
# ============================================================================


class TestGetAsset:
    def test_success(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "获取资产成功",
            "code": 200,
            "data": {
                "total_asset": 1800000.0,
                "market_value": 800000.0,
                "cash": 950000.0,
                "frozen_cash": 50000.0,
                "available_cash": 900000.0,
            },
        }
        mock_http_client.get.return_value = mock_response

        asset = proxy_client.get_asset("session_xxx")

        assert isinstance(asset, QmtAccountInfo)
        assert asset.total_asset == 1800000.0
        assert asset.available_cash == 900000.0
        assert asset.market_value == 800000.0

    def test_fallback_available_cash(self, proxy_client, mock_http_client):
        """没有 available_cash 字段时回退到 cash"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "获取资产成功",
            "code": 200,
            "data": {
                "total_asset": 100000.0,
                "cash": 50000.0,
                "frozen_cash": 0,
                "market_value": 50000.0,
            },
        }
        mock_http_client.get.return_value = mock_response

        asset = proxy_client.get_asset("session_xxx")
        assert asset.available_cash == 50000.0  # fallback to cash


class TestGetPositions:
    def test_success(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "获取持仓成功",
            "code": 200,
            "data": {
                "items": [
                    {
                        "stock_code": "000001.SZ",
                        "instrument_name": "平安银行",
                        "volume": 10000,
                        "can_use_volume": 5000,
                        "frozen_volume": 5000,
                        "avg_price": 12.5,
                        "last_price": 13.2,
                        "market_value": 132000.0,
                        "profit_rate": 0.056,
                    },
                    {
                        "stock_code": "600519.SH",
                        "other": "field",
                        "volume": 200,
                    },
                ]
            },
        }
        mock_http_client.get.return_value = mock_response

        positions = proxy_client.get_positions("session_xxx")

        assert len(positions) == 2
        p1 = positions[0]
        assert isinstance(p1, QmtPosition)
        assert p1.stock_code == "000001.SZ"
        assert p1.volume == 10000
        assert p1.available_volume == 5000
        assert p1.cost_price == 12.5
        assert p1.market_price == 13.2
        assert p1.profit_loss_ratio == 0.056

        p2 = positions[1]
        assert p2.stock_code == "600519.SH"

    def test_empty(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "获取持仓成功",
            "code": 200,
            "data": {"items": []},
        }
        mock_http_client.get.return_value = mock_response
        positions = proxy_client.get_positions("session_xxx")
        assert positions == []


# ============================================================================
# 健康检查
# ============================================================================


class TestHealth:
    def test_alive(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_http_client.get.return_value = mock_response

        assert proxy_client.health() is True

    def test_dead(self, proxy_client, mock_http_client):
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        assert proxy_client.health() is False


# ============================================================================
# 错误处理
# ============================================================================


class TestErrorHandling:
    def test_http_500(self, proxy_client, mock_http_client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "success": False,
            "message": "Internal server error",
            "code": 500,
        }
        mock_http_client.post.return_value = mock_response

        with pytest.raises(QmtProxyError) as exc_info:
            proxy_client.open_session("test")
        assert "500" in str(exc_info.value) or "500" in str(exc_info.value.status_code)

    def test_connection_error(self, proxy_client, mock_http_client):
        mock_http_client.post.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(httpx.ConnectError):
            proxy_client.open_session("test")


# ============================================================================
# stock_code_to_qmt
# ============================================================================


class TestStockCodeToQmt:
    def test_sh_stock(self):
        """6开头的股票 -> 沪市"""
        assert stock_code_to_qmt("600519") == "600519.SH"
        assert stock_code_to_qmt("600519.SH") == "600519.SH"

    def test_sz_stock(self):
        """0/3开头的股票 -> 深市"""
        assert stock_code_to_qmt("000001") == "000001.SZ"
        assert stock_code_to_qmt("000001.SZ") == "000001.SZ"
        assert stock_code_to_qmt("300750") == "300750.SZ"

    def test_bj_stock(self):
        """4/8开头的股票 -> 北交所"""
        assert stock_code_to_qmt("430017") == "430017.BJ"
        assert stock_code_to_qmt("830799") == "830799.BJ"

    def test_already_suffixed(self):
        """已有后缀保持不变"""
        assert stock_code_to_qmt("600519.SH") == "600519.SH"
        assert stock_code_to_qmt("000001.SZ") == "000001.SZ"

    def test_case_insensitive(self):
        """不区分大小写"""
        assert stock_code_to_qmt("600519.sh") == "600519.SH"
        assert stock_code_to_qmt("000001.sz") == "000001.SZ"

    def test_unknown_code(self):
        """无法判断的代码原样返回"""
        assert stock_code_to_qmt("ABCDE") == "ABCDE"


# ============================================================================
# 响应解析边界情况
# ============================================================================


class TestParseResponseEdgeCases:
    def test_non_json_response(self, proxy_client, mock_http_client):
        """非 JSON 响应触发 QmtProxyError"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("expecting value")

        mock_http_client.get.return_value = mock_response

        with pytest.raises(QmtProxyError) as exc_info:
            proxy_client.get_asset("session_xxx")
        assert "响应解析失败" in str(exc_info.value)
