"""Auth 路由 — 集成测试 (test_api_auth.py)

使用 FastAPI TestClient + mock DB session 测试所有 auth 端点。
不连接真实数据库，所有 SQLAlchemy 查询通过 MagicMock 模拟。
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jose import jwt

from src.api.deps import get_current_user_id, hash_password, verify_password
from src.api.routes.auth import router
from src.config import settings
from src.db.models import Sessions, SystemConfig, Users

# ============================================================
# Fixtures：创建测试 App 和 TestClient
# ============================================================


@pytest.fixture
def app():
    """创建一个仅包含 auth 路由的测试用 FastAPI 应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """TestClient 实例"""
    return TestClient(app)


# ============================================================
# 辅助函数
# ============================================================


def _create_access_token(user_id: int = 1, jti: str | None = None) -> str:
    """生成一个有效的 access token 用于测试"""
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": jti or str(uuid.uuid4()),
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _create_refresh_token(user_id: int = 1, jti: str | None = None) -> str:
    """生成一个有效的 refresh token 用于测试"""
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": jti or str(uuid.uuid4()),
            "type": "refresh",
            "iss": settings.JWT_ISSUER,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(days=7),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ============================================================
# GET /api/v1/auth/status 测试
# ============================================================


class TestSystemStatus:
    def test_status_not_initialized(self, client, app):
        """系统未初始化时返回正确的状态"""
        mock_db = MagicMock()

        # 模拟 DB：没有用户，没有 system_initialized 配置
        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.first.return_value = None
            elif model == SystemConfig:
                q.filter_by.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = mock_query_side_effect

        app.dependency_overrides.clear()
        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_initialized"] is False
        assert data["has_user"] is False
        assert data["trade_mode"] == "SIMULATION"

    def test_status_initialized(self, client, app):
        """系统已初始化时返回正确的状态"""
        mock_db = MagicMock()

        mock_user = MagicMock(spec=Users)
        mock_user.id = 1
        mock_user.username = "admin"

        mock_init_config = MagicMock(spec=SystemConfig)
        mock_init_config.config_value = "true"
        mock_trade_mode_config = MagicMock(spec=SystemConfig)
        mock_trade_mode_config.config_value = "PAPER"

        # 记录每次 filter_by 调用的参数
        filter_by_calls = []

        def mock_filter_by(**kwargs):
            filter_by_calls.append(kwargs)
            q = MagicMock()
            if kwargs.get("config_key") == "system_initialized":
                q.first.return_value = mock_init_config
            elif kwargs.get("config_key") == "trade_mode":
                q.first.return_value = mock_trade_mode_config
            else:
                q.first.return_value = None
            return q

        mock_query = MagicMock()
        mock_query.filter_by.side_effect = mock_filter_by
        mock_query.first.side_effect = None  # for Users query

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.first.return_value = mock_user
            elif model == SystemConfig:
                return mock_query
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_initialized"] is True
        assert data["has_user"] is True
        assert data["trade_mode"] == "PAPER"


# ============================================================
# POST /api/v1/auth/setup 测试
# ============================================================


class TestSetup:
    def test_setup_success(self, client, app):
        """首次设置成功创建用户并返回 token"""
        mock_db = MagicMock()

        # 模拟 query 返回 None 表示系统未初始化
        def mock_query_side_effect(model):
            q = MagicMock()
            q.first.return_value = None  # Users.first() 返回 None
            q.filter_by.return_value.first.return_value = None  # SystemConfig 查询也返回 None
            return q

        mock_db.query.side_effect = mock_query_side_effect
        mock_db.add.side_effect = lambda obj: None
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/setup",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_setup_system_already_initialized(self, client, app):
        """系统已初始化时返回 400"""
        mock_db = MagicMock()
        mock_init_config = MagicMock(spec=SystemConfig)
        mock_init_config.config_value = "true"

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == SystemConfig:
                q.filter_by.return_value.first.return_value = mock_init_config
            elif model == Users:
                q.first.return_value = None
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/setup",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 400
        assert "系统已初始化" in resp.text


# ============================================================
# POST /api/v1/auth/login 测试
# ============================================================


class TestLogin:
    def test_login_success(self, client, app):
        """正确用户名密码返回 token"""
        mock_db = MagicMock()
        hashed = hash_password("correct_password")

        mock_user = MagicMock(spec=Users)
        mock_user.id = 1
        mock_user.username = "test_user"
        mock_user.password_hash = hashed
        mock_user.last_login = None
        mock_user.login_count = 0

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.filter_by.return_value.first.return_value = mock_user
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "test_user", "password": "correct_password"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_failure_wrong_password(self, client, app):
        """错误密码返回 401"""
        mock_db = MagicMock()
        hashed = hash_password("correct_password")

        mock_user = MagicMock(spec=Users)
        mock_user.password_hash = hashed

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.filter_by.return_value.first.return_value = mock_user
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "test_user", "password": "wrong_password"},
        )
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.text

    def test_login_failure_user_not_found(self, client, app):
        """用户不存在返回 401"""
        mock_db = MagicMock()

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.filter_by.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "any_password"},
        )
        assert resp.status_code == 401


# ============================================================
# POST /api/v1/auth/refresh 测试
# ============================================================


class TestRefreshToken:
    def test_refresh_success(self, client, app):
        """用有效的 refresh token 换取新 access token"""
        mock_db = MagicMock()

        refresh_jti = str(uuid.uuid4())
        mock_session = MagicMock(spec=Sessions)
        mock_session.refresh_jti = refresh_jti
        mock_session.revoked = False

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Sessions:
                q.filter_by.return_value.first.return_value = mock_session
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        refresh_token = _create_refresh_token(user_id=1, jti=refresh_jti)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client, app):
        """无效 refresh token 返回 401"""
        mock_db = MagicMock()

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_refresh_revoked_session(self, client, app):
        """已撤销的会话返回 401"""
        mock_db = MagicMock()

        refresh_jti = str(uuid.uuid4())

        # filter_by(revoked=False) 不应该返回已撤销的会话
        # 所以 mock 直接返回 None → 找不到有效会话
        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Sessions:
                q.filter_by.return_value.first.return_value = None  # 找不到有效会话
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        refresh_token = _create_refresh_token(user_id=1, jti=refresh_jti)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401
        assert "会话已过期" in resp.text


# ============================================================
# POST /api/v1/auth/logout 测试
# ============================================================


class TestLogout:
    def test_logout_success(self, client, app):
        """正常登出返回成功消息"""
        mock_db = MagicMock()

        # Mock 会话列表
        mock_session1 = MagicMock(spec=Sessions)
        mock_session2 = MagicMock(spec=Sessions)
        mock_db.query.return_value.filter_by.return_value.all.return_value = [
            mock_session1,
            mock_session2,
        ]

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db

        # Mock get_current_user_id 返回固定 user_id
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "已登出"
        assert mock_session1.revoked is True
        assert mock_session2.revoked is True
        assert mock_db.commit.called

    def test_logout_without_token(self, client, app):
        """未提供 token 时返回 401"""
        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: MagicMock()

        resp = client.post("/api/v1/auth/logout")  # 无 Authorization header
        # get_current_user_id 会从 HTTPBearer 读取，没有则返回 401
        # 但我们没 override get_current_user_id，所以需要看实际行为
        # 这里只测无 token 的情况
        assert resp.status_code in (401, 403)


# ============================================================
# POST /api/v1/auth/change-password 测试
# ============================================================


class TestChangePassword:
    def test_change_password_success(self, client, app):
        """正确原密码可修改密码"""
        mock_db = MagicMock()
        hashed_old = hash_password("old_password")

        mock_user = MagicMock(spec=Users)
        mock_user.password_hash = hashed_old

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.filter_by.return_value.first.return_value = mock_user
            elif model == Sessions:
                q.filter_by.return_value.all.return_value = [MagicMock(spec=Sessions)]
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"old_password": "old_password", "new_password": "new_password_123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "密码已修改"

    def test_change_password_wrong_old_password(self, client, app):
        """原密码错误时返回 400"""
        mock_db = MagicMock()
        hashed_old = hash_password("real_old_password")

        mock_user = MagicMock(spec=Users)
        mock_user.password_hash = hashed_old

        def mock_query_side_effect(model):
            q = MagicMock()
            if model == Users:
                q.filter_by.return_value.first.return_value = mock_user
            return q

        mock_db.query.side_effect = mock_query_side_effect

        from src.db.session import get_session

        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_current_user_id] = lambda: 1

        access_token = _create_access_token()
        resp = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"old_password": "wrong_old_password", "new_password": "new_password_123"},
        )
        assert resp.status_code == 400
        assert "原密码错误" in resp.text
