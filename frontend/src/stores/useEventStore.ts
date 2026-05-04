/**
 * FraxVerse · 风控事件状态管理（Zustand）
 *
 * 管理实时候事件列表（止损/风控告警），驱动 MobileMonitor 即时更新。
 * 由 useWebSocketEvents hook 收到 STOP_LOSS_TRIGGERED / RISK_ALERT 时自动写入。
 */

import { create } from "zustand";
import type { WsEventPayload } from "../hooks/useWebSocketEvents";

/** 风控事件（前端轻量版） */
export interface RiskEventItem {
  id: string;
  event_type: string;
  event_level: string;
  trigger_reason: string;
  action_taken: string;
  created_at: string;
  data: Record<string, unknown>;
}

const MAX_EVENTS = 100;

interface EventStore {
  events: RiskEventItem[];
  /** 最新事件（用于弹窗高亮） */
  latestEvent: WsEventPayload | null;

  /** 添加风控相关事件 */
  push: (event: WsEventPayload) => void;
  /** 重置 */
  reset: () => void;
}

/** 风控相关的事件类型 */
const RISK_EVENT_TYPES = new Set([
  "STOP_LOSS_TRIGGERED",
  "STOP_PROFIT_TRIGGERED",
  "RISK_ALERT",
  "MARKET_EXTREME",
  "SYSTEM_ERROR",
]);

export const useEventStore = create<EventStore>((set) => ({
  events: [],
  latestEvent: null,

  push: (event) => {
    if (!RISK_EVENT_TYPES.has(event.event_type)) return;

    const item: RiskEventItem = {
      id: event.event_id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      event_type: event.title || event.event_type,
      event_level:
        event.level === "critical" || event.level === "high"
          ? "warning"
          : "info",
      trigger_reason: event.body,
      action_taken: event.data?.action_taken as string || "pending",
      created_at: event.timestamp
        ? new Date(event.timestamp * 1000).toISOString()
        : new Date().toISOString(),
      data: event.data,
    };

    set((state) => ({
      events: [item, ...state.events].slice(0, MAX_EVENTS),
      latestEvent: event,
    }));
  },

  reset: () => {
    set({ events: [], latestEvent: null });
  },
}));
