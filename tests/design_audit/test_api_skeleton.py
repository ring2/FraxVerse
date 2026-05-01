"""
设计审查：FastAPI API 骨架 vs 详细设计文档
"""
from pathlib import Path

API_DIR = Path("/home/ubuntu/FraxVerse/src/api")


def test_auth_router_exists():
    """auth 路由文件应存在"""
    assert (API_DIR / "routes" / "auth.py").exists()


def test_trade_router_exists():
    """trade 路由文件应存在"""
    assert (API_DIR / "routes" / "trade.py").exists()


def test_market_router_exists():
    """market 路由文件应存在"""
    assert (API_DIR / "routes" / "market.py").exists()


def test_misc_routers_exist():
    """strategy/agent/risk/experience/monitor/notifications 路由应存在"""
    assert (API_DIR / "routes" / "misc.py").exists()


def test_deps_exists():
    """依赖项文件应存在（JWT/密码/当前用户）"""
    assert (API_DIR / "deps.py").exists()


def test_main_app_exists():
    """主入口文件应存在"""
    assert (API_DIR / "main.py").exists()


def test_schemas_exist():
    """Schema 文件应存在"""
    schema_dir = Path("/home/ubuntu/FraxVerse/src/schemas")
    assert (schema_dir / "auth.py").exists()
    assert (schema_dir / "trade.py").exists()
    assert (schema_dir / "market.py").exists()
    assert (schema_dir / "agent.py").exists()
    assert (schema_dir / "system.py").exists()


def test_api_routes_registered():
    """验证所有路由前缀已在main.py中注册"""
    content = (API_DIR / "main.py").read_text()
    expected_routes = [
        "auth_router",
        "trade_router",
        "market_router",
        "strategy_router",
        "agent_router",
        "risk_router",
        "experience_router",
        "monitor_router",
        "notification_router",
    ]
    for route in expected_routes:
        assert route in content, f"main.py 缺少 {route} 注册"


def test_auth_endpoints_defined():
    """auth 路由应包含所有标准端点"""
    content = (API_DIR / "routes" / "auth.py").read_text()
    endpoints = ["@router.get(\"/status\"", "@router.post(\"/setup\"", "@router.post(\"/login\"",
                 "@router.post(\"/refresh\"", "@router.post(\"/logout\""]
    for ep in endpoints:
        assert ep in content, f"auth.py 缺少 {ep}"


def test_health_endpoint():
    """main.py 应包含 /api/v1/health"""
    content = (API_DIR / "main.py").read_text()
    assert "/api/v1/health" in content


def test_cors_middleware():
    """应配置 CORS 中间件"""
    content = (API_DIR / "main.py").read_text()
    assert "CORSMiddleware" in content
