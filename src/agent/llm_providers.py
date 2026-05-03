"""
FraxVerse · LLM 厂商预设表 + 连接管理 + API 适配器

=== 设计哲学（V2 重构） ===
第 1 层：厂商预设（本文件）—— 厂商名、默认 URL、API 格式
第 2 层：连接配置（llm_provider_connections 表）—— 用户配的 Key/URL 覆盖
第 3 层：使用分配（system_config 表）—— 每日分析用哪个连接+模型

厂商预设只提供默认值，不存储用户敏感信息。
模型列表只用于前端下拉展示，不参与后端调用逻辑。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from sqlalchemy.orm import Session

from src.db.session import Base

logger = logging.getLogger(__name__)


# ─── 厂商预设 ────────────────────────────────────────────────────


@dataclass
class LLMProviderPreset:
    """LLM 厂商预设（纯信息，不存用户密钥）"""
    name: str                        # 厂商名（唯一标识）
    label: str                       # 显示名
    default_base_url: str            # 默认 API 地址
    api_format: Literal["openai", "claude", "gemini"] = "openai"
    doc_url: str = ""


# 厂商预设表 — 去掉 models 列表，只保留连接信息
LLM_PROVIDERS: dict[str, LLMProviderPreset] = {
    # ─── 国内 ───
    "deepseek": LLMProviderPreset(
        name="deepseek", label="DeepSeek",
        default_base_url="https://api.deepseek.com",
        doc_url="https://platform.deepseek.com/api-docs",
    ),
    "zhipu": LLMProviderPreset(
        name="zhipu", label="智谱 GLM",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        doc_url="https://open.bigmodel.cn/dev/api",
    ),
    "moonshot": LLMProviderPreset(
        name="moonshot", label="月之暗面 Moonshot",
        default_base_url="https://api.moonshot.cn/v1",
        doc_url="https://platform.moonshot.cn/docs",
    ),
    "qwen": LLMProviderPreset(
        name="qwen", label="阿里通义千问",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        doc_url="https://help.aliyun.com/zh/model-studio/",
    ),
    "baidu": LLMProviderPreset(
        name="baidu", label="百度文心",
        default_base_url="https://aip.baidubce.com/rpc/2.0/ai_custom",
        doc_url="https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Fm2vrveyu",
    ),
    "doubao": LLMProviderPreset(
        name="doubao", label="字节豆包",
        default_base_url="https://ark.cn-beijing.volces.com/api/v3",
        doc_url="https://www.volcengine.com/docs/82379",
    ),
    "yi": LLMProviderPreset(
        name="yi", label="零一万物 Yi",
        default_base_url="https://api.lingyiwanwu.com/v1",
        doc_url="https://platform.lingyiwanwu.com/docs",
    ),
    "baichuan": LLMProviderPreset(
        name="baichuan", label="百川智能",
        default_base_url="https://api.baichuan-ai.com/v1",
        doc_url="https://platform.baichuan-ai.com/docs",
    ),
    "skywork": LLMProviderPreset(
        name="skywork", label="昆仑万维天工",
        default_base_url="https://api.skywork.com/v1",
        doc_url="https://skywork.com/docs",
    ),
    "siliconflow": LLMProviderPreset(
        name="siliconflow", label="SiliconFlow（聚合）",
        default_base_url="https://api.siliconflow.cn/v1",
        doc_url="https://docs.siliconflow.cn/api-reference",
    ),
    # ─── 国外 ───
    "openai": LLMProviderPreset(
        name="openai", label="OpenAI",
        default_base_url="https://api.openai.com",
        doc_url="https://platform.openai.com/docs",
    ),
    "anthropic": LLMProviderPreset(
        name="anthropic", label="Anthropic Claude",
        default_base_url="https://api.anthropic.com",
        doc_url="https://docs.anthropic.com/en/docs",
        api_format="claude",
    ),
    "gemini": LLMProviderPreset(
        name="gemini", label="Google Gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        doc_url="https://ai.google.dev/gemini-api/docs",
        api_format="gemini",
    ),
    "xai": LLMProviderPreset(
        name="xai", label="xAI Grok",
        default_base_url="https://api.x.ai",
        doc_url="https://docs.x.ai/docs",
    ),
    "mistral": LLMProviderPreset(
        name="mistral", label="Mistral AI",
        default_base_url="https://api.mistral.ai/v1",
        doc_url="https://docs.mistral.ai",
    ),
}


def get_provider_preset(provider_name: str) -> LLMProviderPreset | None:
    """按厂商名查找预设"""
    return LLM_PROVIDERS.get(provider_name)


def get_all_provider_presets() -> list[dict[str, Any]]:
    """获取所有厂商预设（纯信息，无密钥）"""
    return [
        {
            "name": p.name,
            "label": p.label,
            "default_base_url": p.default_base_url,
            "api_format": p.api_format,
        }
        for p in sorted(LLM_PROVIDERS.values(), key=lambda x: x.label)
    ]


# ─── 模型预设表（仅前端展示用） ──────────────────────────────

# 每个厂商的推荐模型列表 + 默认模型
# 不影响后端逻辑，只给前端下拉提供选项
LLM_MODEL_PRESETS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "models": [
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v4-flash",
            "deepseek-v4-0524",
            "deepseek-v3",
            "deepseek-r1",
        ],
        "default_model": "deepseek-chat",
    },
    "zhipu": {
        "models": [
            "glm-4-plus",
            "glm-4-0520",
            "glm-4-air-0111",
            "glm-4-flash-250331",
            "glm-4-flash",
            "glm-4v-plus",
        ],
        "default_model": "glm-4-plus",
    },
    "moonshot": {
        "models": [
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
            "moonshot-v1-auto",
        ],
        "default_model": "moonshot-v1-8k",
    },
    "qwen": {
        "models": [
            "qwen-plus-2025-04-28",
            "qwen-plus",
            "qwen-max-2025-04-25",
            "qwen-max",
            "qwen-turbo-2025-04-28",
            "qwen-turbo",
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct",
            "qwen-vl-max",
        ],
        "default_model": "qwen-plus",
    },
    "baidu": {
        "models": [
            "ernie-4.0-8k-latest",
            "ernie-4.0-turbo-8k-latest",
            "ernie-3.5-8k-preview",
            "ernie-speed-128k",
            "ernie-lite-8k-0922",
        ],
        "default_model": "ernie-4.0-8k-latest",
    },
    "doubao": {
        "models": [
            "doubao-pro-32k-250415",
            "doubao-pro-128k-250415",
            "doubao-lite-32k-250415",
            "doubao-lite-128k-250415",
            "doubao-1.5-pro-256k-250515",
            "doubao-1.5-lite-32k-250515",
        ],
        "default_model": "doubao-pro-32k-250415",
    },
    "yi": {
        "models": [
            "yi-lightning-250417",
            "yi-lightning",
            "yi-medium",
            "yi-large",
            "yi-large-turbo",
            "yi-vision",
        ],
        "default_model": "yi-lightning",
    },
    "baichuan": {
        "models": [
            "baichuan4-turbo-2504",
            "baichuan4-turbo",
            "baichuan4-air-2504",
            "baichuan4-air",
            "baichuan3-turbo",
        ],
        "default_model": "baichuan4-turbo-2504",
    },
    "skywork": {
        "models": [
            "skywork-turbo-2501",
            "skywork-turbo",
            "skywork-premium",
        ],
        "default_model": "skywork-turbo-2501",
    },
    "siliconflow": {
        "models": [
            "deepseek-ai/DeepSeek-V3-250324",
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1-250324",
            "deepseek-ai/DeepSeek-R1",
            "Pro/deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-72B-Instruct-128K",
            "Qwen/Qwen2.5-32B-Instruct",
            "Qwen/QwQ-32B-Preview",
            "THUDM/glm-4-9b-chat",
        ],
        "default_model": "deepseek-ai/DeepSeek-V3-250324",
    },
    "openai": {
        "models": [
            "gpt-4o-2025-04-17",
            "gpt-4o",
            "gpt-4o-mini-2025-04-17",
            "gpt-4o-mini",
            "gpt-4.1-2025-04-17",
            "gpt-4.1",
            "gpt-4.1-mini-2025-04-17",
            "gpt-4.1-mini",
            "gpt-4.1-nano-2025-04-17",
            "gpt-4.1-nano",
            "o4-mini-2025-04-17",
            "o4-mini",
            "o3-2025-04-17",
            "o3",
        ],
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "models": [
            "claude-sonnet-4-20250514",
            "claude-sonnet-4",
            "claude-opus-4-20250514",
            "claude-haiku-3-5-20241022",
            "claude-haiku-3-5",
        ],
        "default_model": "claude-sonnet-4",
    },
    "gemini": {
        "models": [
            "gemini-2.5-pro-04-17",
            "gemini-2.5-flash-04-17",
            "gemini-2.5-pro-exp-03-25",
            "gemini-2.5-flash-preview-04-17",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ],
        "default_model": "gemini-2.5-pro-04-17",
    },
    "xai": {
        "models": [
            "grok-3-250422",
            "grok-3",
            "grok-3-mini-250422",
            "grok-3-mini",
            "grok-2-250422",
            "grok-2",
        ],
        "default_model": "grok-3-250422",
    },
    "mistral": {
        "models": [
            "mistral-large-2504",
            "mistral-large-2411",
            "mistral-small-2501",
            "pixtral-large-2503",
            "pixtral-large-2411",
            "codestral-2505",
            "codestral-2501",
        ],
        "default_model": "mistral-large-2504",
    },
}


def get_provider_models(provider_name: str) -> list[str]:
    """获取指定厂商的推荐模型列表"""
    info = LLM_MODEL_PRESETS.get(provider_name)
    return info["models"] if info else []


def get_all_providers_with_models() -> list[dict[str, Any]]:
    """获取所有厂商预设+模型列表（用于前端）"""
    result = []
    for p in sorted(LLM_PROVIDERS.values(), key=lambda x: x.label):
        model_info = LLM_MODEL_PRESETS.get(p.name, {"models": [], "default_model": ""})
        result.append({
            "name": p.name,
            "label": p.label,
            "default_base_url": p.default_base_url,
            "api_format": p.api_format,
            "models": model_info["models"],
            "default_model": model_info["default_model"],
        })
    return result


# ─── 连接管理（DB） ──────────────────────────────────────────


class LLMProviderConnection(Base):
    """厂商连接配置 — 用户保存的 API Key / Base URL 覆盖"""
    __tablename__ = "llm_provider_connections"

    id: int = None  # auto PK
    provider_name: str = None  # 厂商名（对应预设中的 name）
    label: str = ""  # 用户自定义标签（可选）
    api_key: str = ""  # 加密存储（TODO）
    base_url: str = ""  # 留空 = 使用厂商预设的默认 URL
    is_deleted: bool = False
    created_at: Any = None
    updated_at: Any = None

    # 用 sqlalchemy 的 Column 定义
    from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
    from sqlalchemy import text as sa_text

    __table_args__ = (
        # provider_name 应唯一（每厂商只配一条连接）
    )


def create_connections_table_if_not_exists(db: Session):
    """创建 llm_provider_connections 表（如果不存在）"""
    from sqlalchemy import inspect, text as sa_text
    inspector = inspect(db.bind)
    if not inspector.has_table("llm_provider_connections"):
        # 建表
        db.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS llm_provider_connections (
                id SERIAL PRIMARY KEY,
                provider_name VARCHAR(50) NOT NULL UNIQUE,
                label VARCHAR(100) NOT NULL DEFAULT '',
                api_key TEXT NOT NULL DEFAULT '',
                base_url TEXT NOT NULL DEFAULT '',
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
        """))
        db.commit()


def get_connections(db: Session) -> list[dict[str, Any]]:
    """获取用户配置的所有厂商连接"""
    from sqlalchemy import text as sa_text
    create_connections_table_if_not_exists(db)
    rows = db.execute(
        sa_text("SELECT * FROM llm_provider_connections WHERE is_deleted = FALSE ORDER BY provider_name")
    ).fetchall()
    return [
        {
            "id": r.id,
            "provider_name": r.provider_name,
            "label": r.label,
            "has_api_key": bool(r.api_key),
            "base_url": r.base_url,
        }
        for r in rows
    ]


def get_connection(db: Session, provider_name: str) -> dict[str, Any] | None:
    """获取指定厂商的连接（含真实 API Key）"""
    from sqlalchemy import text as sa_text
    create_connections_table_if_not_exists(db)
    row = db.execute(
        sa_text("SELECT * FROM llm_provider_connections WHERE provider_name = :pn AND is_deleted = FALSE"),
        {"pn": provider_name},
    ).fetchone()
    if not row:
        return None
    return {
        "id": row.id,
        "provider_name": row.provider_name,
        "label": row.label,
        "api_key": row.api_key,
        "base_url": row.base_url,
    }


def upsert_connection(
    db: Session,
    provider_name: str,
    api_key: str,
    base_url: str = "",
    label: str = "",
) -> dict[str, Any]:
    """创建或更新厂商连接"""
    from sqlalchemy import text as sa_text
    create_connections_table_if_not_exists(db)
    existing = db.execute(
        sa_text("SELECT id FROM llm_provider_connections WHERE provider_name = :pn"),
        {"pn": provider_name},
    ).fetchone()
    if existing:
        db.execute(
            sa_text("""
                UPDATE llm_provider_connections
                SET api_key = :ak, base_url = :bu, label = :lb, updated_at = NOW()
                WHERE provider_name = :pn
            """),
            {"ak": api_key, "bu": base_url, "lb": label, "pn": provider_name},
        )
    else:
        db.execute(
            sa_text("""
                INSERT INTO llm_provider_connections (provider_name, label, api_key, base_url)
                VALUES (:pn, :lb, :ak, :bu)
            """),
            {"pn": provider_name, "lb": label, "ak": api_key, "bu": base_url},
        )
    db.commit()
    return get_connection(db, provider_name)


def delete_connection(db: Session, provider_name: str):
    """软删除厂商连接"""
    from sqlalchemy import text as sa_text
    db.execute(
        sa_text("UPDATE llm_provider_connections SET is_deleted = TRUE WHERE provider_name = :pn"),
        {"pn": provider_name},
    )
    db.commit()


def resolve_llm_config(
    db: Session,
    usage_key: str | None = None,
) -> dict[str, Any]:
    """
    解析 LLM 调用配置。

    1. 如果指定了 usage_key（如 'daily_analysis'），从 system_config 读取该用途的配置
    2. 从连接表读取对应厂商的连接信息
    3. 回退逻辑：关键决策模型 → 复用每日分析

    返回: {
        "provider_name": str,
        "model": str,
        "api_key": str,
        "base_url": str,
        "api_format": str,
    }
    """
    from sqlalchemy import text as sa_text

    if usage_key:
        # 读取用途配置
        provider_cfg = db.execute(
            sa_text("SELECT config_value FROM system_config WHERE config_key = :ck"),
            {"ck": f"{usage_key}_provider"},
        ).scalar()
        model_cfg = db.execute(
            sa_text("SELECT config_value FROM system_config WHERE config_key = :ck"),
            {"ck": f"{usage_key}_model"},
        ).scalar()
        reuse = db.execute(
            sa_text("SELECT config_value FROM system_config WHERE config_key = :ck"),
            {"ck": f"{usage_key}_reuse"},
        ).scalar()

        # 如果启用了复用，递归获取被复用的配置
        provider_name = provider_cfg or None
        model = model_cfg or None

        if provider_name and model:
            pass  # 有完整配置
        elif reuse == "true" or (not provider_name):
            # 回退到每日分析
            return resolve_llm_config(db, usage_key="daily_analysis")

        if not provider_name or not model:
            # 没有任何配置，用默认
            provider_name = "deepseek"
            model = "deepseek-chat"
    else:
        provider_name = "deepseek"
        model = "deepseek-chat"

    # 读取连接信息
    preset = get_provider_preset(provider_name)
    conn = get_connection(db, provider_name)

    api_key = (conn["api_key"] if conn else "") or ""
    base_url = (conn["base_url"] if conn and conn["base_url"] else "") or (preset.default_base_url if preset else "https://api.openai.com")
    api_format = preset.api_format if preset else "openai"

    return {
        "provider_name": provider_name,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "api_format": api_format,
    }


# ─── API 适配器（不变） ─────────────────────────────────────────


def _build_openai_payload(
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    use_json: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    if use_json:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int = 2,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    use_json = "json" in (system_prompt + user_prompt).lower()
    payload = _build_openai_payload(model, system_prompt, user_prompt, timeout, use_json)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}"
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)
                    continue
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                break
        except httpx.TimeoutException as e:
            last_error = f"timeout: {e}"
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue

    raise RuntimeError(f"OpenAI API call failed: {last_error}")


def _call_claude_api(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int = 2,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "choices": [{"message": {"content": data["content"][0]["text"]}}],
                    "model": model,
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    },
                }
            elif resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}"
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)
                    continue
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                break
        except httpx.TimeoutException as e:
            last_error = f"timeout: {e}"
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue

    raise RuntimeError(f"Claude API call failed: {last_error}")


def _call_gemini_api(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int = 2,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.7,
        },
    }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                resp = client.post(url, headers=headers, params=params, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    for part in candidates[0].get("content", {}).get("parts", []):
                        text += part.get("text", "")
                return {
                    "choices": [{"message": {"content": text}}],
                    "model": model,
                    "usage": {
                        "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                        "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                    },
                }
            elif resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}"
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)
                    continue
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue

    raise RuntimeError(f"Gemini API call failed: {last_error}")


# ─── 统一调用入口 ────────────────────────────────────────────


def call_llm_with_provider(
    provider_name: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 60,
    base_url_override: str | None = None,
    max_retries: int = 2,
) -> tuple[str, str, dict[str, int]]:
    provider = get_provider_preset(provider_name)
    if provider is None:
        logger.warning("Unknown provider '%s', falling back to OpenAI format", provider_name)
        base_url = base_url_override or "https://api.openai.com"
        api_format = "openai"
    else:
        base_url = base_url_override or provider.default_base_url
        api_format = provider.api_format

    if api_format == "claude":
        data = _call_claude_api(base_url, api_key, model, system_prompt, user_prompt, timeout, max_retries)
    elif api_format == "gemini":
        data = _call_gemini_api(base_url, api_key, model, system_prompt, user_prompt, timeout, max_retries)
    else:
        data = _call_openai_compatible(base_url, api_key, model, system_prompt, user_prompt, timeout, max_retries)

    choice = data["choices"][0]
    content = choice["message"]["content"]
    actual_model = data.get("model", model)
    usage = data.get("usage", {})
    usage_dict = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }
    return content, actual_model, usage_dict
