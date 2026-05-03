"""FraxVerse 数据库连接与会话管理"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://fraxverse:fraxverse_dev@localhost:5432/fraxverse",
)

SYNC_DB_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://fraxverse:fraxverse_dev@localhost:5432/fraxverse",
)

engine = create_engine(
    SYNC_DB_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_session():
    """获取同步会话（用于初始化、seed等）"""
    return SessionLocal()


def check_db_health() -> bool:
    """检查数据库连接是否正常"""
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
