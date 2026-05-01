"""数据库连接管理

提供统一的 PostgreSQL 和 Redis 连接工厂。
"""
import os

import psycopg2
import redis


def get_db_connection():
    """获取 PostgreSQL 连接（自动从环境变量读取配置）"""
    return psycopg2.connect(
        host=os.environ.get("FRAXVERSE_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("FRAXVERSE_DB_PORT", "5432")),
        dbname=os.environ.get("FRAXVERSE_DB_NAME", "fraxverse"),
        user=os.environ.get("FRAXVERSE_DB_USER", "postgres"),
        password=os.environ.get("FRAXVERSE_DB_PASSWORD", "fraxverse_dev_2026!"),
    )


def get_redis_connection() -> redis.Redis:
    """获取 Redis 连接"""
    return redis.Redis(
        host=os.environ.get("FRAXVERSE_REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("FRAXVERSE_REDIS_PORT", "6379")),
        db=0,
        decode_responses=True,
    )
