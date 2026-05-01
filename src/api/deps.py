"""
FraxVerse · API 依赖项

包含：JWT创建/验证、密码哈希、当前用户提取
"""
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import Sessions
from src.db.session import get_session

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=settings.BCRYPT_ROUNDS)

# Bearer Token 安全方案
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """bcrypt哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_tokens(user_id: int, db: Session) -> dict:
    """创建 Access Token + Refresh Token，并记录会话"""
    now = datetime.now(UTC)

    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        "sub": str(user_id),
        "jti": access_jti,
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    refresh_payload = {
        "sub": str(user_id),
        "jti": refresh_jti,
        "type": "refresh",
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }

    access_token = jwt.encode(access_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # 记录会话
    session = Sessions(
        user_id=user_id,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        access_expires=datetime.fromtimestamp(access_payload["exp"], tz=UTC),
        refresh_expires=datetime.fromtimestamp(refresh_payload["exp"], tz=UTC),
    )
    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> int:
    """从 Bearer Token 提取当前用户ID"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="缺少认证信息")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="无效的Token类型")
        jti = payload.get("jti")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    # 检查会话是否有效
    session = db.query(Sessions).filter_by(access_jti=jti, revoked=False).first()
    if not session:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")

    return user_id


class AllowAny:
    """用于无需认证的端点（如 /auth/login、/auth/status）"""
    pass
