"""Trade 路由 — 集成测试 (test_api_trade.py)

使用 FastAPI TestClient + mock DB session 测试所有 trade 端点。
不连接真实数据库，所有 SQLAlchemy 查询通过 MagicMock 模拟。
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from src.api.deps import get_current_user_id
from src.api.routes.trade import router
from src.config import settings
from src.db.models import Positions, StockPool, TradeMode, TradeOrders, Stocks

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _create_access_token(user_id: int = 1) -> str:
    """生成有效的 access token"""
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ============================================================
# GET /api/v1/trade/orders 测试
# ============================================================


class TestListOrders:
    def test_get_orders_returns_list(self, client, app):
        """返回订单列表"""
        mock_db = MagicMock()

        mock_order = MagicMock(spec=TradeOrders)
        mock_order.id = 1
        mock_order.client_order_id = str(uuid.uuid4())
        mock_order.stock_code = "600519.SH"
        mock_order.direction = "buy"
        mock_order.status = "filled"
        mock_order.volume = 100
        mock_order.filled_volume = 100
        mock_order.price = Decimal("150.00")
        mock_order.created_at = datetime.now(UTC)

        # Mock 查询链
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_order
        ]

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/orders",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["stock_code"] == "600519.SH"
        assert data[0]["direction"] == "buy"

    def test_get_orders_with_status_filter(self, client, app):
        """按状态筛选订单"""
        mock_db = MagicMock()

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == TradeOrders:
                # Mock order_by → filter → limit → all
                order_q = MagicMock()
                q.order_by.return_value = order_q
            return q

        mock_db.query.side_effect = mock_query_side_effect
        mock_db.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = []

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/orders?status=filled",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_orders_without_auth(self, client, app):
        """未认证返回 401"""
        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: MagicMock()

        resp = client.get("/api/v1/trade/orders")
        assert resp.status_code in (401, 403)


# ============================================================
# GET /api/v1/trade/orders/{order_id} 测试
# ============================================================


class TestGetOrder:
    def test_get_order_found(self, client, app):
        """查询存在的订单"""
        mock_db = MagicMock()
        mock_order = MagicMock(spec=TradeOrders)
        mock_order.id = 42
        mock_order.client_order_id = str(uuid.uuid4())
        mock_order.stock_code = "000001.SZ"
        mock_order.direction = "sell"
        mock_order.status = "pending"
        mock_order.volume = 200
        mock_order.filled_volume = 0
        mock_order.price = Decimal("10.50")
        mock_order.created_at = datetime.now(UTC)

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_order

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/orders/42",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == 42

    def test_get_order_not_found(self, client, app):
        """查询不存在的订单返回 404"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/orders/999",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 404
        assert "订单不存在" in resp.text


# ============================================================
# POST /api/v1/trade/orders 测试
# ============================================================


class TestCreateOrder:
    def test_create_order_simulation(self, client, app):
        """SIMULATION 模式下创建订单直接标记为 filled"""
        mock_db = MagicMock()

        # Mock TradeMode 返回 SIMULATION
        mock_mode = MagicMock(spec=TradeMode)
        mock_mode.current_mode = "SIMULATION"

        # Mock order 被 refresh 后获得 id 和 created_at
        mock_order_to_return = None

        def mock_refresh(obj):
            obj.id = 100
            obj.created_at = datetime.now(UTC)

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == TradeMode:
                q.first.return_value = mock_mode
            return q

        mock_db.query.side_effect = mock_query_side_effect
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = mock_refresh

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/orders",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "stock_code": "600519.SH",
                "direction": "buy",
                "order_type": "market",
                "volume": 100,
                "price": 150.00,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "filled"
        assert data["stock_code"] == "600519.SH"
        assert data["id"] == 100

    def test_create_order_pending_in_live_mode(self, client, app):
        """LIVE 模式下创建订单标记为 pending"""
        mock_db = MagicMock()

        mock_mode = MagicMock(spec=TradeMode)
        mock_mode.current_mode = "LIVE"

        def mock_refresh(obj):
            obj.id = 101
            obj.created_at = datetime.now(UTC)

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == TradeMode:
                q.first.return_value = mock_mode
            return q

        mock_db.query.side_effect = mock_query_side_effect
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = mock_refresh

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/orders",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "stock_code": "600519.SH",
                "direction": "buy",
                "order_type": "limit",
                "volume": 100,
                "price": 150.00,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["id"] == 101


# ============================================================
# POST /api/v1/trade/orders/{order_id}/cancel 测试
# ============================================================


class TestCancelOrder:
    def test_cancel_order_success(self, client, app):
        """撤销 pending 状态订单"""
        mock_db = MagicMock()
        mock_order = MagicMock(spec=TradeOrders)
        mock_order.status = "pending"

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_order

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/orders/1/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert mock_order.status == "cancelled"

    def test_cancel_order_not_found(self, client, app):
        """撤销不存在的订单返回 404"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/orders/999/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 404

    def test_cancel_filled_order(self, client, app):
        """撤销已成交订单返回 400"""
        mock_db = MagicMock()
        mock_order = MagicMock(spec=TradeOrders)
        mock_order.status = "filled"

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_order

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/orders/1/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 400


# ============================================================
# GET /api/v1/trade/positions 测试
# ============================================================


class TestListPositions:
    def test_get_positions_returns_list(self, client, app):
        """返回持仓列表"""
        mock_db = MagicMock()

        mock_position = MagicMock(spec=Positions)
        mock_position.stock_code = "600519.SH"
        mock_position.total_volume = 1000
        mock_position.available_volume = 500
        mock_position.cost_price = Decimal("150.00")
        mock_position.market_value = Decimal("160000.00")
        mock_position.unrealized_pnl = Decimal("10000.00")
        mock_position.unrealized_pnl_pct = Decimal("6.67")
        mock_position.position_pct = Decimal("25.00")
        mock_position.entry_date = datetime.now(UTC).date()

        # Mock 股票名称
        mock_stock = MagicMock(spec=Stocks)
        mock_stock.name = "贵州茅台"

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Positions:
                q.filter.return_value.all.return_value = [mock_position]
            elif model == Stocks:
                q.filter_by.return_value.first.return_value = mock_stock
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/positions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["stock_code"] == "600519.SH"
        assert data[0]["stock_name"] == "贵州茅台"
        assert data[0]["total_volume"] == 1000

    def test_get_positions_empty(self, client, app):
        """无持仓时返回空列表"""
        mock_db = MagicMock()

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Positions:
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/positions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ============================================================
# GET /api/v1/trade/pool 测试
# ============================================================


class TestStockPool:
    def test_get_pool_returns_list(self, client, app):
        """返回股票池列表"""
        mock_db = MagicMock()

        mock_pool_item = MagicMock(spec=StockPool)
        mock_pool_item.date = datetime.now(UTC).date()
        mock_pool_item.stock_code = "600519.SH"
        mock_pool_item.strategy_type = "trend_momentum"
        mock_pool_item.pass_coarse = True
        mock_pool_item.score_total = Decimal("85.50")
        mock_pool_item.final_decision = "buy"
        mock_pool_item.position_pct = Decimal("10.00")
        mock_pool_item.reject_reason = None

        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_pool_item
        ]

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/pool",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_pool_with_strategy_filter(self, client, app):
        """按策略筛选股票池"""
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = []

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/pool?strategy=bottom_volume",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ============================================================
# GET /api/v1/trade/mode 测试
# ============================================================


class TestGetTradeMode:
    def test_get_trade_mode_with_data(self, client, app):
        """TradeMode 表有数据时返回正确值"""
        mock_db = MagicMock()

        mock_mode = MagicMock(spec=TradeMode)
        mock_mode.current_mode = "SIMULATION"
        mock_mode.confirm_mode = "advisory"
        mock_mode.emergency_stop = False

        mock_db.query.return_value.first.return_value = mock_mode

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/mode",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_mode"] == "SIMULATION"
        assert data["confirm_mode"] == "advisory"
        assert data["emergency_stop"] is False

    def test_get_trade_mode_default_when_no_data(self, client, app):
        """TradeMode 表无数据时返回默认值"""
        mock_db = MagicMock()
        mock_db.query.return_value.first.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.get(
            "/api/v1/trade/mode",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_mode"] == "SIMULATION"
        assert data["confirm_mode"] == "advisory"
        assert data["emergency_stop"] is False


# ============================================================
# POST /api/v1/trade/mode 测试
# ============================================================


class TestUpdateTradeMode:
    def test_update_mode_success(self, client, app):
        """切换交易模式成功"""
        mock_db = MagicMock()

        mock_mode = MagicMock(spec=TradeMode)
        mock_mode.current_mode = "SIMULATION"

        mock_db.query.return_value.first.return_value = mock_mode

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/mode",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"target_mode": "PAPER"},
        )
        assert resp.status_code == 200
        assert mock_mode.current_mode == "PAPER"

    def test_update_mode_not_initialized(self, client, app):
        """TradeMode 表未初始化时返回 500"""
        mock_db = MagicMock()
        mock_db.query.return_value.first.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/mode",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"target_mode": "LIVE"},
        )
        assert resp.status_code == 500
        assert "未初始化" in resp.text


# ============================================================
# POST /api/v1/trade/emergency-stop 测试
# ============================================================


class TestEmergencyStop:
    def test_emergency_stop_success(self, client, app):
        """紧急停止成功"""
        mock_db = MagicMock()

        mock_mode = MagicMock(spec=TradeMode)
        mock_mode.emergency_stop = False
        mock_mode.emergency_stopped_at = None

        mock_db.query.return_value.first.return_value = mock_mode

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/emergency-stop",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert mock_mode.emergency_stop is True
        assert mock_mode.emergency_stopped_at is not None

    def test_emergency_stop_not_initialized(self, client, app):
        """TradeMode 未初始化时返回 500"""
        mock_db = MagicMock()
        mock_db.query.return_value.first.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/trade/emergency-stop",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 500
