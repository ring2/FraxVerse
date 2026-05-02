import api from "./api";
import type {
  SystemResource,
  ServiceStatus,
} from "../types/api-extended";

export const monitorService = {
  /**
   * GET /api/v1/monitor/resources
   * 系统资源 — 返回 SystemResource 对象
   * 注意：后端缺少 psutil 时可能返回 500，此处用 ?? null 保护
   */
  async getResources(): Promise<SystemResource | null> {
    const res = await api.get("/monitor/resources");
    return res.data ?? null;
  },

  /**
   * GET /api/v1/monitor/services
   * 服务状态 — 返回 ServiceStatus[] 数组
   */
  async getServices(): Promise<ServiceStatus[]> {
    const res = await api.get("/monitor/services");
    return Array.isArray(res.data) ? res.data : [];
  },
};
