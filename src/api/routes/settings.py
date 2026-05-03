"""设置路由 — /api/v1/settings/*"""

from typing import Any

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.models import SystemConfig
from src.db.session import get_session

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _cast_config_value(config_value: str, config_type: str) -> Any:
    """按 config_type 将字符串值转为对应的 Python 类型"""
    if config_type == "bool":
        return config_value.lower() == "true"
    elif config_type == "number":
        try:
            if "." in config_value:
                return float(config_value)
            return int(config_value)
        except (ValueError, TypeError):
            return config_value
    elif config_type == "json":
        import json
        try:
            return json.loads(config_value)
        except (ValueError, TypeError):
            return config_value
    elif config_type == "array":
        import json
        try:
            parsed = json.loads(config_value)
            if isinstance(parsed, list):
                return parsed
            return config_value
        except (ValueError, TypeError):
            return config_value
    # string 或其它类型，直接返回
    return config_value


@router.get("/configs")
def get_configs(
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """获取全部配置，值按 config_type 转换类型"""
    configs = db.query(SystemConfig).all()
    result: dict[str, Any] = {}
    for cfg in configs:
        result[cfg.config_key] = _cast_config_value(cfg.config_value, cfg.config_type)
    return result


@router.put("/configs")
def update_configs(
    body: dict[str, Any],
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, str]:
    """批量更新配置 — 接收 dict，仅更新传了的 key，不存在的 key 自动创建"""
    updated: list[str] = []
    created: list[str] = []

    for key, value in body.items():
        # 将 Python 值转为字符串
        str_value: str
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            str_value = str(value)
        elif value is None:
            str_value = ""
        else:
            str_value = str(value)

        existing = db.query(SystemConfig).filter_by(config_key=key).first()
        if existing:
            existing.config_value = str_value
            updated.append(key)
        else:
            # 自动推断 config_type
            config_type = "string"
            if isinstance(value, bool):
                config_type = "bool"
            elif isinstance(value, int) and not isinstance(value, bool):
                config_type = "number"
            elif isinstance(value, float):
                config_type = "number"
            db.add(SystemConfig(
                config_key=key,
                config_value=str_value,
                config_type=config_type,
                description=None,
            ))
            created.append(key)

    db.commit()
    msg = f"已更新 {len(updated)} 项，新增 {len(created)} 项"
    return {"message": msg, "updated": str(updated), "created": str(created)}


@router.get("/llm-providers")
def get_llm_providers(
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """获取所有 LLM 厂商预设（用于前端下拉菜单）"""
    from src.agent.llm_providers import get_all_providers
    return get_all_providers()
