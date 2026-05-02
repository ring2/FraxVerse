import api from "./api";
import type { PortfolioSummary, PositionItem } from "../types/api-extended";

export const portfolioService = {
  /**
   * GET /api/v1/portfolio/summary
   * 账户总览 — 直接返回裸 PortfolioSummary 对象
   */
  async getSummary(): Promise<PortfolioSummary | null> {
    const res = await api.get("/portfolio/summary");
    return res.data ?? null;
  },

  /**
   * GET /api/v1/trade/positions
   * 当前持仓 — 直接返回 PositionItem[] 数组
   */
  async getPositions(): Promise<PositionItem[]> {
    const res = await api.get("/trade/positions");
    // 后端直接返回裸数组，res.data 就是数组本身
    return Array.isArray(res.data) ? res.data : [];
  },
};
