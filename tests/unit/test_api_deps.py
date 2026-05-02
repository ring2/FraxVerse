"""API 依赖层 — 单元测试 (test_api_deps.py)

测试 src.api.deps 中的纯逻辑函数和需要 mock DB 的函数。
使用 unittest.mock 模拟所有数据库交互，不连接真实数据库。
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt

from src.api.deps import (
    AllowAny,
    create_tokens,
    get_current_user_id,
    hash_password,
    verify_password,
)
from src.config import settings


# ============================================================
# 密码相关测试（纯逻辑，无外部依赖）
# ============================================================


class TestHashPassword:
    def test_hash_password_creates_hash(self):
        """哈希不为空，且不包含原始密码"""
        hashed = hash_password("my_secret_pass_123")
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt 前缀
        assert "my_secret_pass_123" not in hashed

    def test_hash_different_inputs_different_hashes(self):
        """不同输入生成不同哈希（bcrypt 自带 salt）"""
        h1 = hash_password("password_1")
        h2 = hash_password("password_2")
        assert h1 != h2

    def test_hash_same_input_different_hashes(self):
        """相同输入因 salt 不同也会生成不同哈希"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestVerifyPassword:
    def test_verify_correct_password(self):
        """正确密码返回 True"""
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_wrong_password(self):
        """错误密码返回 False"""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_empty_password(self):
        """空密码验证"""
        hashed = hash_password("some_password")
        assert verify_password("", hashed) is False


# ============================================================
# create_tokens 测试（需要 mock DB session）
# ============================================================


class TestCreateTokens:
    def test_create_tokens_returns_expected_structure(self):
        """create_tokens 返回包含 access/refresh token 的 dict"""
        mock_db = MagicMock()
        result = create_tokens(user_id=1, db=mock_db)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # 验证 JWT 可以被解码
        payload = jwt.decode(
            result["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

        refresh_payload = jwt.decode(
            result["refresh_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert refresh_payload["sub"] == "1"
        assert refresh_payload["type"] == "refresh"

        # 验证 DB session 被调用
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_create_tokens_stores_session_in_db(self):
        """验证会话记录被添加到 DB"""
        mock_db = MagicMock()
        user_id = 42
        result = create_tokens(user_id=user_id, db=mock_db)

        # 检查添加到 DB 的 Session 对象
        added_session = mock_db.add.call_args[0][0]
        assert added_session.user_id == user_id
        assert added_session.access_jti is not None
        assert added_session.refresh_jti is not None
        # revoked 字段在模型中有 server_default="FALSE"，但 mock 不会应用默认值
        # 所以只验证对象被添加且 commit 被调用
        assert added_session.access_expires is not None
        assert added_session.refresh_expires is not None


# ============================================================
# get_current_user_id 测试（需要 mock credentials + DB）
# ============================================================


class TestGetCurrentUserId:
    def test_missing_credentials_raises_401(self):
        """无凭证时返回 401"""
        with pytest.raises(HTTPException) as exc:
            get_current_user_id(credentials=None, db=MagicMock())
        assert exc.value.status_code == 401
        assert "缺少认证信息" in str(exc.value.detail)

    def test_invalid_token_raises_401(self):
        """无效 JWT 返回 401"""
        bad_creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.jwt.token"
        )
        with pytest.raises(HTTPException) as exc:
            get_current_user_id(credentials=bad_creds, db=MagicMock())
        assert exc.value.status_code == 401

    def test_wrong_token_type_raises_401(self):
        """非 access 类型的 token 返回 401"""
        refresh_token = jwt.encode(
            {"sub": "1", "jti": str(uuid.uuid4()), "type": "refresh", "iss": settings.JWT_ISSUER},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=refresh_token)
        with pytest.raises(HTTPException) as exc:
            get_current_user_id(credentials=creds, db=MagicMock())
        assert exc.value.status_code == 401
        assert "无效的Token类型" in str(exc.value.detail)

    def test_revoked_session_raises_401(self):
        """会话已被撤销时返回 401"""
        access_token = jwt.encode(
            {"sub": "1", "jti": str(uuid.uuid4()), "type": "access", "iss": settings.JWT_ISSUER},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)

        # Mock DB — 返回已撤销的会话
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None  # 找不到有效会话

        with pytest.raises(HTTPException) as exc:
            get_current_user_id(credentials=creds, db=mock_db)
        assert exc.value.status_code == 401
        assert "会话已过期" in str(exc.value.detail)

    def test_valid_token_returns_user_id(self):
        """有效 access token 返回 user_id"""
        jti = str(uuid.uuid4())
        access_token = jwt.encode(
            {
                "sub": "5",
                "jti": jti,
                "type": "access",
                "iss": settings.JWT_ISSUER,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(minutes=30),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)

        # Mock DB session
        mock_session_obj = MagicMock()
        mock_session_obj.revoked = False

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_session_obj

        user_id = get_current_user_id(credentials=creds, db=mock_db)
        assert user_id == 5


# ============================================================
# AllowAny 测试
# ============================================================


class TestAllowAny:
    def test_allow_any_is_passable_class(self):
        """AllowAny 是一个可实例化的标记类"""
        instance = AllowAny()
        assert instance is not None
