import api from "./api";
import { normalizeStockCode } from "../utils/stockCode";
import type {
  OrderResponse,
  OrderCreateRequest,
  TradeModeResponse,
} from "../types/api-extended";
import type { components } from "../types/api-generated";

type TradeModeUpdateRequest = components["schemas"]["TradeModeUpdateRequest"];

export const tradeService = {
  /**
   * GET /api/v1/trade/orders
   * 订单列表 — 返回 OrderResponse[] 数组
   */
  async getOrders(): Promise<OrderResponse[]> {
    const res = await api.get("/trade/orders");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/trade/orders/:orderId
   * 单个订单详情 — 返回 OrderResponse 对象
   */
  async getOrder(orderId: string): Promise<OrderResponse | null> {
    const res = await api.get(`/trade/orders/${orderId}`);
    return res.data ?? null;
  },

  /**
   * POST /api/v1/trade/orders
   * 创建订单 — 传入 OrderCreateRequest，返回新增的 OrderResponse
   */
  async createOrder(payload: OrderCreateRequest): Promise<OrderResponse | null> {
    const res = await api.post("/trade/orders", {
      ...payload,
      stock_code: normalizeStockCode(payload.stock_code),
    });
    return res.data ?? null;
  },

  /**
   * POST /api/v1/trade/orders/:orderId/cancel
   * 撤单
   */
  async cancelOrder(orderId: string): Promise<void> {
    await api.post(`/trade/orders/${orderId}/cancel`);
  },

  /**
   * GET /api/v1/trade/mode
   * 交易模式 — 返回 TradeModeResponse 对象
   */
  async getMode(): Promise<TradeModeResponse | null> {
    const res = await api.get("/trade/mode");
    return res.data ?? null;
  },

  /**
   * POST /api/v1/trade/mode
   * 更新交易模式 — 传入 TradeModeUpdateRequest
   */
  async updateMode(payload: TradeModeUpdateRequest): Promise<TradeModeResponse | null> {
    const res = await api.post("/trade/mode", payload);
    return res.data ?? null;
  },

  /**
   * POST /api/v1/trade/emergency-stop
   * 紧急停止
   */
  async emergencyStop(): Promise<void> {
    await api.post("/trade/emergency-stop");
  },
};
