"""PostgreSQL 和 Redis 连接验证测试"""
import pytest


def test_postgres_connection():
    """验证 PostgreSQL 连接正常"""
    import psycopg2
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="fraxverse",
        user="fraxverse",
        password="fraxverse_dev",
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()


def test_redis_connection():
    """验证 Redis 连接正常"""
    import redis
    r = redis.Redis(host="127.0.0.1", port=6379, db=0)
    assert r.ping()


def test_database_has_all_tables():
    """验证数据库包含全部预期表（35张）"""
    import psycopg2
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="fraxverse",
        user="fraxverse",
        password="fraxverse_dev",
    )
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert count >= 35, f"预期至少35张表，实际{count}张"
