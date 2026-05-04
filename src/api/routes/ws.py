"""
FraxVerse · WebSocket 路由 — /api/v1/ws/*

实时事件推送：监听 Redis EventBus 通道，通过 WebSocket 推送到前端。
每个连接独立监听，断连自动清理。
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from src.config import settings
from src.eventbus.bus import Event, EventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

# ── Redis 监听线程 ────────────────────────────────────────────

# 映射: {websocket: (thread, pubsub)}
_active_connections: dict[WebSocket, tuple[threading.Thread, Any]] = {}


def _verify_ws_token(token: str) -> int | None:
    """验证 WebSocket 连接携带的 JWT token，返回 user_id 或 None"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return int(payload.get("sub", 0))
    except JWTError:
        return None


def _redis_listener(websocket: WebSocket, channel_pattern: str) -> None:
    """
    后台线程：监听 Redis Pub/Sub，收到消息后通过 WebSocket 推送。

    运行在独立线程中，websocket.send_text() 是异步调用，
    但这里使用 asyncio.run() 在子线程中运行协程。
    """
    import redis as redis_lib

    try:
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        # 监听所有 EventBus 通道 fraxverse:events:*
        pubsub.psubscribe(channel_pattern)
        logger.info(
            "Redis listener started for %s (pattern=%s)",
            id(websocket),
            channel_pattern,
        )

        for message in pubsub.listen():
            if message.get("type") == "pmessage":
                data = message.get("data", "")
                if not data:
                    continue
                # 反序列化，补充 title/body/level 字段再推
                try:
                    payload = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    continue

                # 构造前端友好格式
                event_type_name = payload.get("event_type", "UNKNOWN")
                event_data = payload.get("data", {})

                ws_payload = _build_ws_message(event_type_name, event_data, payload)

                # 异步推送
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(websocket.send_text(json.dumps(ws_payload, default=str)))
                    loop.close()
                except Exception:
                    logger.warning("WS send failed for %s, stopping listener", id(websocket))
                    break

        pubsub.close()
        r.close()
    except Exception as exc:
        logger.warning("Redis listener exited for %s: %s", id(websocket), exc)
    finally:
        _active_connections.pop(websocket, None)


def _build_ws_message(
    event_type_name: str,
    event_data: dict,
    raw_payload: dict,
) -> dict:
    """将后端 Event 转换为前端友好的 WS 消息格式"""
    # 中文标题映射
    title_map: dict[str, str] = {
        "STOP_LOSS_TRIGGERED": "止损触发",
        "STOP_PROFIT_TRIGGERED": "止盈触发",
        "RISK_ALERT": "风控告警",
        "POSITION_OPENED": "开仓通知",
        "POSITION_CLOSED": "平仓通知",
        "MARKET_EXTREME": "极端行情",
        "TRADE_SIGNAL_GENERATED": "交易信号",
        "SYSTEM_ERROR": "系统错误",
    }
    stock_code = event_data.get("stock_code", "")
    title = title_map.get(event_type_name, event_type_name)

    # 根据 event_type 映射 level
    level_map: dict[str, str] = {
        "STOP_LOSS_TRIGGERED": "high",
        "STOP_PROFIT_TRIGGERED": "normal",
        "RISK_ALERT": "high",
        "SYSTEM_ERROR": "critical",
        "MARKET_EXTREME": "critical",
        "POSITION_OPENED": "normal",
        "POSITION_CLOSED": "normal",
        "TRADE_SIGNAL_GENERATED": "normal",
    }
    level = level_map.get(event_type_name, "normal")

    # 构造 body
    loss_pct = event_data.get("loss_pct") or event_data.get("loss_pct", 0)
    reason = event_data.get("reason", "")

    body_parts = []
    if stock_code:
        body_parts.append(stock_code)
    if loss_pct:
        body_parts.append(f"{loss_pct:+.1%}" if isinstance(loss_pct, float) else str(loss_pct))
    if reason:
        body_parts.append(reason)
    body = " ".join(body_parts) if body_parts else event_type_name

    return {
        "event_type": event_type_name,
        "source": raw_payload.get("source", "system"),
        "timestamp": raw_payload.get("timestamp", 0),
        "event_id": raw_payload.get("event_id", ""),
        "title": title,
        "body": body,
        "level": level,
        "data": event_data,
    }


# ── WebSocket 端点 ────────────────────────────────────────────


@router.websocket("/events")
async def ws_events(
    websocket: WebSocket,
    token: str = Query(""),
):
    """
    WebSocket 端点 — 实时事件推送

    用法：
        ws://host/api/v1/ws/events?token=<access_token>

    连接成功后，系统事件会实时推送。格式：
        {event_type, source, timestamp, event_id, title, body, level, data}
    """
    # 1. 验证 JWT
    user_id = _verify_ws_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # 2. 接受连接
    await websocket.accept()
    logger.info("WS connected: user=%s ws=%s", user_id, id(websocket))

    # 3. 启动 Redis 监听线程
    listener_thread = threading.Thread(
        target=_redis_listener,
        args=(websocket, "fraxverse:events:*"),
        daemon=True,
    )
    listener_thread.start()
    _active_connections[websocket] = (listener_thread, None)

    # 4. 保持连接：等待客户端断开或异常
    try:
        while True:
            # 接收客户端消息（心跳 pong 或忽略）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WS disconnected: user=%s ws=%s", user_id, id(websocket))
    except Exception as exc:
        logger.warning("WS error: user=%s %s", user_id, exc)
    finally:
        _active_connections.pop(websocket, None)
