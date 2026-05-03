import api from "./api";
import type {
  KlineItem,
  MarketStateResponse,
  SectorItem,
  NewsItem,
} from "../types/api-extended";

export interface KlinesParams {
  stock_code: string;
  period?: string;
  limit?: number;
}

export const marketService = {
  /**
   * GET /api/v1/market/klines?stock_code=XXX&period=daily&limit=N
   * 日K线数据 — 返回 KlineItem[] 数组
   */
  async getKlines(params: KlinesParams): Promise<KlineItem[]> {
    const res = await api.get("/market/klines", { params });
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/market/market-state
   * 市场状态 — 返回 MarketStateResponse 对象
   * 注意：后端可能返回空对象 {}，此时返回 null
   */
  async getMarketState(): Promise<MarketStateResponse | null> {
    const res = await api.get("/market/market-state");
    const data = res.data;
    if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
      return null;
    }
    return data as MarketStateResponse;
  },

  /**
   * GET /api/v1/market/sectors
   * 板块数据 — 返回 SectorItem[] 数组
   */
  async getSectors(): Promise<SectorItem[]> {
    const res = await api.get("/market/sectors");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/market/news
   * 新闻分页 — 返回 { items, total }
   */
  async getNews(params?: {
    offset?: number;
    limit?: number;
    source?: string;
    hot_only?: boolean;
  }): Promise<{ items: NewsItem[]; total: number }> {
    const res = await api.get("/market/news", { params });
    const data = res.data;
    if (data && "items" in data && "total" in data) {
      return { items: data.items as NewsItem[], total: data.total as number };
    }
    return { items: [], total: 0 };
  },

  /**
   * GET /api/v1/market/stock-detail?code=XXX
   * 个股详情（实时行情 + 日K）
   */
  async getStockDetail(code: string): Promise<Record<string, unknown>> {
    const res = await api.get("/market/stock-detail", { params: { code } });
    return (res.data || {}) as Record<string, unknown>;
  },
};
