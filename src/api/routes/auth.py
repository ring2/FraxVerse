"""认证路由 — /api/v1/auth/*"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id, hash_password, verify_password
from src.db.models import Sessions, SystemConfig, Users
from src.db.session import get_session
from src.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    SetupRequest,
    SystemInitStatus,
    TokenResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/status", response_model=SystemInitStatus)
def get_system_status(db: Session = Depends(get_session)):
    """检查系统是否已初始化"""
    user = db.query(Users).first()
    sys_init = db.query(SystemConfig).filter_by(config_key="system_initialized").first()
    trade_mode = db.query(SystemConfig).filter_by(config_key="trade_mode").first()
    return SystemInitStatus(
        is_initialized=(sys_init.config_value == "true" if sys_init else False),
        has_user=(user is not None),
        trade_mode=trade_mode.config_value if trade_mode else "SIMULATION",
    )


@router.post("/setup", response_model=TokenResponse)
def setup_system(req: SetupRequest, db: Session = Depends(get_session)):
    """首次设置 — 创建用户 + 初始化系统"""
    # 检查是否已初始化
    sys_init = db.query(SystemConfig).filter_by(config_key="system_initialized").first()
    if sys_init and sys_init.config_value == "true":
        raise HTTPException(status_code=400, detail="系统已初始化")

    # 创建用户
    existing = db.query(Users).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户已存在")

    user = Users(
        username=req.username,
        password_hash=hash_password(req.password),
        is_initialized=True,
    )
    db.add(user)
    db.flush()

    # 保存DeepSeek Key
    if req.deepseek_api_key:
        existing_key = db.query(SystemConfig).filter_by(config_key="deepseek_api_key").first()
        if existing_key:
            existing_key.config_value = req.deepseek_api_key
        else:
            db.add(SystemConfig(config_key="deepseek_api_key", config_value=req.deepseek_api_key, config_type="string"))

    # 标记系统已初始化
    init_config = db.query(SystemConfig).filter_by(config_key="system_initialized").first()
    if init_config:
        init_config.config_value = "true"
    else:
        db.add(SystemConfig(config_key="system_initialized", config_value="true", config_type="bool"))

    db.commit()

    # 返回Token
    from src.api.deps import create_tokens
    tokens = create_tokens(user.id, db)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_session)):
    """用户登录"""
    user = db.query(Users).filter_by(username=req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 更新登录信息
    user.last_login = datetime.now(UTC)
    user.login_count = (user.login_count or 0) + 1
    db.commit()

    from src.api.deps import create_tokens
    tokens = create_tokens(user.id, db)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_session)):
    """用Refresh Token换取新的Access Token"""
    from jose import JWTError, jwt

    from src.config import settings

    try:
        payload = jwt.decode(
            req.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的Token类型")
        user_id = payload.get("sub")
        jti = payload.get("jti")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    # 检查会话是否被撤销
    session = db.query(Sessions).filter_by(refresh_jti=jti, revoked=False).first()
    if not session:
        raise HTTPException(status_code=401, detail="会话已过期")

    # 撤销旧会话，创建新Token
    session.revoked = True
    db.commit()

    from src.api.deps import create_tokens
    tokens = create_tokens(user_id, db)
    return TokenResponse(**tokens)


@router.post("/logout")
def logout(db: Session = Depends(get_session), user_id: int = Depends(get_current_user_id)):
    """登出 — 撤销当前用户所有活跃会话"""
    sessions = db.query(Sessions).filter_by(user_id=user_id, revoked=False).all()
    for s in sessions:
        s.revoked = True
    db.commit()
    return {"message": "已登出"}


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """修改密码"""
    user = db.query(Users).filter_by(id=user_id).first()
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password_hash = hash_password(req.new_password)
    # 撤销所有会话
    sessions = db.query(Sessions).filter_by(user_id=user_id, revoked=False).all()
    for s in sessions:
        s.revoked = True
    db.commit()
    return {"message": "密码已修改"}
