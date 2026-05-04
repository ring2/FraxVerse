/**
 * FraxVerse · WebSocket 事件实时推送 Hook
 *
 * 连接 /api/v1/ws/events?token=xxx，自动重连，心跳保持。
 * 收到事件后写入 Zustand store，驱动 UI 实时更新。
 */

import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "../stores/useAuthStore";
import { useNotificationStore } from "../stores/useNotificationStore";

/** WS 收到的事件格式 */
export interface WsEventPayload {
  event_type: string;
  source: string;
  timestamp: number;
  event_id: string;
  title: string;
  body: string;
  level: string;
  data: Record<string, unknown>;
}

/** 15 分钟 reconnect 上限，超过不再重试 */
const MAX_RECONNECT_DELAY = 900_000;
const INITIAL_RECONNECT_DELAY = 3_000;
const HEARTBEAT_INTERVAL = 30_000;

function getWsBaseUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  // 开发模式 Vite proxy 走 /ws
  if (import.meta.env.DEV) {
    return `${proto}//${host}`;
  }
  return `${proto}//${host}`;
}

let globalReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let globalHeartbeatTimer: ReturnType<typeof setInterval> | null = null;

export function useWebSocketEvents() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const isActiveRef = useRef(false);

  const connect = useCallback(() => {
    const accessToken = useAuthStore.getState().accessToken;
    if (!accessToken) {
      // Not logged in, retry in a bit
      globalReconnectTimer = setTimeout(() => connect(), INITIAL_RECONNECT_DELAY);
      return;
    }

    // Close existing if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const url = `${getWsBaseUrl()}/api/v1/ws/events?token=${encodeURIComponent(accessToken)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] Connected to event stream");
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;

      // Start heartbeat
      if (globalHeartbeatTimer) clearInterval(globalHeartbeatTimer);
      globalHeartbeatTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (evt: MessageEvent) => {
      try {
        const event: WsEventPayload = JSON.parse(evt.data);
        // Skip heartbeat responses
        if (event === "pong" as unknown as WsEventPayload) return;
        console.log("[WS] Event received:", event.event_type, event.title);

        // Push to notification store
        useNotificationStore.getState().add(event);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      console.log("[WS] Disconnected");
      wsRef.current = null;
      clearHeartbeat();
      scheduleReconnect();
    };

    ws.onerror = () => {
      console.warn("[WS] Error, will reconnect");
      ws.close();
    };
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (!isActiveRef.current) return;
    const delay = reconnectDelayRef.current;
    reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);

    console.log(`[WS] Reconnecting in ${delay / 1000}s...`);
    globalReconnectTimer = setTimeout(() => connect(), delay);
  }, [connect]);

  const clearHeartbeat = useCallback(() => {
    if (globalHeartbeatTimer) {
      clearInterval(globalHeartbeatTimer);
      globalHeartbeatTimer = null;
    }
  }, []);

  // Mount / unmount
  useEffect(() => {
    isActiveRef.current = true;
    connect();

    return () => {
      isActiveRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (globalReconnectTimer) {
        clearTimeout(globalReconnectTimer);
        globalReconnectTimer = null;
      }
      clearHeartbeat();
    };
  }, [connect, clearHeartbeat]);

  return { wsRef };
}

/**
 * 在应用顶层调用的组件，挂载一个 WebSocket 连接。
 * 放在 App.tsx 或 main.tsx 的 Suspense 外层即可。
 */
export function WebSocketProvider({ children }: { children: any }) {
  useWebSocketEvents();
  return children;
}
