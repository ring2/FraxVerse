import api from "./api";
import type { NotificationItem } from "../types/api-extended";

export const notificationService = {
  /**
   * GET /api/v1/notifications/
   * 通知列表 — 返回 NotificationItem[] 数组
   */
  async getNotifications(): Promise<NotificationItem[]> {
    const res = await api.get("/notifications/");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * POST /api/v1/notifications/:id/read
   * 标记通知为已读
   */
  async markRead(id: string): Promise<void> {
    await api.post(`/notifications/${id}/read`);
  },
};
