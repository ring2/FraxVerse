"""
FraxVerse (碎片宇宙) · FastAPI 配置模块

环境变量 & 应用配置
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "FraxVerse"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据库
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://fraxverse:fraxverse_dev@localhost:5432/fraxverse",
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://fraxverse:fraxverse_dev@localhost:5432/fraxverse",
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", ""
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "fraxverse"

    # 安全
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    BCRYPT_ROUNDS: int = 12

    # 路径
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    LOG_DIR: Path = PROJECT_ROOT / "logs"

    # LLM
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # quant-qmt-proxy (LIVE 模式对接)
    QMT_PROXY_URL: str = os.getenv("QMT_PROXY_URL", "http://127.0.0.1:8000")
    QMT_PROXY_API_KEY: str = os.getenv("QMT_PROXY_API_KEY", "")
    QMT_ACCOUNT_ID: str = os.getenv("QMT_ACCOUNT_ID", "")
    QMT_ACCOUNT_TYPE: str = os.getenv("QMT_ACCOUNT_TYPE", "STOCK")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
