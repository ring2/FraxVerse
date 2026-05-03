"""
FraxVerse · LLM 厂商预设表 + API 适配器

每家主流的 LLM API 都有独立的 base_url 和消息格式。
本模块维护一个厂商预设表，支持：
1. 按厂商名查询默认 base_url
2. 按厂商名获取 API 请求适配器（OpenAI 兼容 / Claude / Gemini）
3. 自定义模型名和自定义 base_url

支持厂商（2026年5月）：
- 国内：DeepSeek, 智谱GLM, 月之暗面Moonshot, 阿里通义千问,
         百度文心, 字节豆包, 零一万物, 百川, 昆仑万维,
         SiliconFlow (聚合平台)
- 国外：OpenAI, Anthropic Claude, Google Gemini, Grok/xAI, Mistral
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


# ─── 厂商模型预设 ─────────────────────────────────────────────


@dataclass
class LLMProvider:
    """LLM 厂商预设"""
    name: str                        # 厂商名（唯一标识）
    label: str                       # 显示名
    base_url: str                    # 默认 API 地址（不含 /v1/chat/completions）
    api_format: Literal["openai", "claude", "gemini"] = "openai"  # 请求格式
    doc_url: str = ""                # API 文档地址
    models: list[str] = field(default_factory=list)  # 推荐模型列表（首项为默认）


# 热门厂商预设表
# key = 厂商标识, 与种子数据 llm_provider 配置项匹配
LLM_PROVIDERS: dict[str, LLMProvider] = {
    # ─── 国内 ───
    "deepseek": LLMProvider(
        name="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        doc_url="https://platform.deepseek.com/api-docs",
        models=[
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v3",
            "deepseek-r1",
        ],
    ),
    "zhipu": LLMProvider(
        name="zhipu",
        label="智谱 GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        doc_url="https://open.bigmodel.cn/dev/api",
        models=[
            "glm-4-plus",
            "glm-4-0520",
            "glm-4-air",
            "glm-4-flash",
        ],
    ),
    "moonshot": LLMProvider(
        name="moonshot",
        label="月之暗面 Moonshot",
        base_url="https://api.moonshot.cn/v1",
        doc_url="https://platform.moonshot.cn/docs",
        models=[
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
        ],
    ),
    "qwen": LLMProvider(
        name="qwen",
        label="阿里通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        doc_url="https://help.aliyun.com/zh/model-studio/",
        models=[
            "qwen-plus",
            "qwen-max",
            "qwen-turbo",
            "qwen2.5-72b-instruct",
        ],
    ),
    "baidu": LLMProvider(
        name="baidu",
        label="百度文心",
        base_url="https://aip.baidubce.com/rpc/2.0/ai_custom",
        doc_url="https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Fm2vrveyu",
        api_format="openai",  # 文心4.0+ 支持 OpenAI 兼容
        models=[
            "ernie-4.0-8k-latest",
            "ernie-3.5-8k-preview",
            "ernie-speed-128k",
            "ernie-lite-8k-0922",
        ],
    ),
    "doubao": LLMProvider(
        name="doubao",
        label="字节豆包",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        doc_url="https://www.volcengine.com/docs/82379",
        models=[
            "doubao-pro-32k",
            "doubao-pro-128k",
            "doubao-lite-32k",
            "doubao-lite-128k",
        ],
    ),
    "yi": LLMProvider(
        name="yi",
        label="零一万物 Yi",
        base_url="https://api.lingyiwanwu.com/v1",
        doc_url="https://platform.lingyiwanwu.com/docs",
        models=[
            "yi-lightning",
            "yi-medium",
            "yi-large",
            "yi-large-turbo",
        ],
    ),
    "baichuan": LLMProvider(
        name="baichuan",
        label="百川智能",
        base_url="https://api.baichuan-ai.com/v1",
        doc_url="https://platform.baichuan-ai.com/docs",
        models=[
            "baichuan4-turbo",
            "baichuan4-air",
            "baichuan3-turbo",
        ],
    ),
    "skywork": LLMProvider(
        name="skywork",
        label="昆仑万维天工",
        base_url="https://api.skywork.com/v1",
        doc_url="https://skywork.com/docs",
        models=[
            "skywork-turbo",
            "skywork-premium",
        ],
    ),
    "siliconflow": LLMProvider(
        name="siliconflow",
        label="SiliconFlow (聚合)",
        base_url="https://api.siliconflow.cn/v1",
        doc_url="https://docs.siliconflow.cn/api-reference",
        models=[
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Pro/deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-72B-Instruct-128K",
            "Qwen/Qwen2.5-32B-Instruct",
        ],
    ),
    # ─── 国外 ───
    "openai": LLMProvider(
        name="openai",
        label="OpenAI",
        base_url="https://api.openai.com",
        doc_url="https://platform.openai.com/docs",
        models=[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "o3",
            "o4-mini",
        ],
    ),
    "anthropic": LLMProvider(
        name="anthropic",
        label="Anthropic Claude",
        base_url="https://api.anthropic.com",
        doc_url="https://docs.anthropic.com/en/docs",
        api_format="claude",
        models=[
            "claude-sonnet-4-20250514",
            "claude-sonnet-4",
            "claude-opus-4-20250514",
            "claude-haiku-3-5",
        ],
    ),
    "gemini": LLMProvider(
        name="gemini",
        label="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        doc_url="https://ai.google.dev/gemini-api/docs",
        api_format="gemini",
        models=[
            "gemini-2.5-pro-exp-03-25",
            "gemini-2.5-flash-preview-04-17",
            "gemini-2.0-flash",
        ],
    ),
    "xai": LLMProvider(
        name="xai",
        label="xAI Grok",
        base_url="https://api.x.ai",
        doc_url="https://docs.x.ai/docs",
        models=[
            "grok-3",
            "grok-3-mini",
            "grok-2",
        ],
    ),
    "mistral": LLMProvider(
        name="mistral",
        label="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        doc_url="https://docs.mistral.ai",
        models=[
            "mistral-large-2411",
            "mistral-small-2501",
            "pixtral-large-2411",
            "codestral-2501",
        ],
    ),
}


def get_provider(provider_name: str) -> LLMProvider | None:
    """按厂商名查找预设"""
    return LLM_PROVIDERS.get(provider_name)


def get_all_providers() -> list[dict[str, Any]]:
    """获取所有厂商预设（用于前端下拉）"""
    return [
        {
            "name": p.name,
            "label": p.label,
            "base_url": p.base_url,
            "api_format": p.api_format,
            "models": p.models,
            "default_model": p.models[0] if p.models else "",
        }
        for p in sorted(LLM_PROVIDERS.values(), key=lambda x: x.label)
    ]


def get_provider_models(provider_name: str) -> list[str]:
    """获取指定厂商的推荐模型列表"""
    p = get_provider(provider_name)
    return p.models if p else []


# ─── OpenAI 兼容格式（90%+ 厂商使用此格式） ────────────────────

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
    """调用 OpenAI 兼容 API（DeepSeek / Moonshot / Qwen / SiliconFlow 等）"""
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


# ─── Claude 格式 ─────────────────────────────────────────────


def _call_claude_api(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int = 2,
) -> dict[str, Any]:
    """调用 Anthropic Claude Messages API"""
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
                # 统一为 OpenAI 兼容格式输出
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                return {
                    "choices": [{"message": {"content": content}}],
                    "model": data.get("model", model),
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
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
                continue

    raise RuntimeError(f"Claude API call failed: {last_error}")


# ─── Gemini 格式 ─────────────────────────────────────────────


def _call_gemini_api(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int = 2,
) -> dict[str, Any]:
    """调用 Google Gemini API"""
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
    }
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
                # 统一为 OpenAI 兼容格式输出
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
    """
    按厂商配置调用 LLM API。

    返回: (content, actual_model, usage_dict)
    usage_dict = {"prompt_tokens": N, "completion_tokens": N}
    """
    provider = get_provider(provider_name)
    if provider is None:
        # 未知厂商 → 默认使用 OpenAI 兼容格式
        logger.warning("Unknown provider '%s', falling back to OpenAI format", provider_name)
        base_url = base_url_override or "https://api.openai.com"
        api_format = "openai"
    else:
        base_url = base_url_override or provider.base_url
        api_format = provider.api_format

    if api_format == "claude":
        data = _call_claude_api(base_url, api_key, model, system_prompt, user_prompt, timeout, max_retries)
    elif api_format == "gemini":
        data = _call_gemini_api(base_url, api_key, model, system_prompt, user_prompt, timeout, max_retries)
    else:
        # openai 兼容（默认）
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
