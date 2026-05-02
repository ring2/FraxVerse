import api from "./api";
import type {
  RiskMetricsItem,
  RiskEventItem,
} from "../types/api-extended";

export const riskService = {
  /**
   * GET /api/v1/risk/metrics
   * 风控指标 — 返回 RiskMetricsItem[] 数组
   */
  async getMetrics(): Promise<RiskMetricsItem[]> {
    const res = await api.get("/risk/metrics");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/risk/events
   * 风控事件 — 返回 RiskEventItem[] 数组
   */
  async getEvents(): Promise<RiskEventItem[]> {
    const res = await api.get("/risk/events");
    return Array.isArray(res.data) ? res.data : [];
  },
};
