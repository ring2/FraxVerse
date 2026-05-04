/**
 * FraxVerse · 通知状态管理（Zustand）
 *
 * 管理实时通知列表、未读计数、最新事件。
 * 由 useWebSocketEvents hook 自动写入。
 */

import { create } from "zustand";
import type { WsEventPayload } from "../hooks/useWebSocketEvents";

/** 通知项 — 包含 WS 事件 + 前端 UI 状态 */
export interface NotificationItem {
  id: string;
  event_id: string;
  event_type: string;
  title: string;
  body: string;
  level: string;
  source: string;
  timestamp: number;
  is_read: boolean;
  created_at: string;
  data: Record<string, unknown>;
}

const MAX_NOTIFICATIONS = 200;

interface NotificationStore {
  /** 通知列表（最新的在前） */
  notifications: NotificationItem[];
  /** 未读数 */
  unreadCount: number;
  /** 最新事件（用于弹窗/提示） */
  latestEvent: WsEventPayload | null;

  /** 添加 WS 事件 */
  add: (event: WsEventPayload) => void;
  /** 标记已读 */
  markRead: (id: string) => void;
  /** 标记全部已读 */
  markAllRead: () => void;
  /** 清空最新事件 */
  clearLatest: () => void;
  /** 重置（登出时调用） */
  reset: () => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  unreadCount: 0,
  latestEvent: null,

  add: (event) => {
    const item: NotificationItem = {
      id: event.event_id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      event_id: event.event_id,
      event_type: event.event_type,
      title: event.title,
      body: event.body,
      level: event.level,
      source: event.source,
      timestamp: event.timestamp,
      is_read: false,
      created_at: event.timestamp
        ? new Date(event.timestamp * 1000).toISOString()
        : new Date().toISOString(),
      data: event.data,
    };

    set((state) => ({
      notifications: [item, ...state.notifications].slice(0, MAX_NOTIFICATIONS),
      unreadCount: state.unreadCount + 1,
      latestEvent: event,
    }));
  },

  markRead: (id) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n,
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    }));
  },

  markAllRead: () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
      unreadCount: 0,
    }));
  },

  clearLatest: () => {
    set({ latestEvent: null });
  },

  reset: () => {
    set({ notifications: [], unreadCount: 0, latestEvent: null });
  },
}));
