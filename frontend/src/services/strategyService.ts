import api from "./api";
import type { StockPoolItem, BacktestResultItem } from "../types/api-extended";

/**
 * 策略参数项 — 后端直接返回的格式，OpenAPI schema 未覆盖此类型
 */
export interface StrategyParamItem {
  id: number;
  strategy_type: string;
  param_key: string;
  description: string;
  param_type: string;
  param_value: string;
  updated_at: string;
}

export const strategyService = {
  /**
   * GET /api/v1/strategy/params
   * 策略参数列表 — 直接返回 StrategyParamItem[] 数组
   */
  async getParams(): Promise<StrategyParamItem[]> {
    const res = await api.get("/strategy/params");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/trade/pool
   * 每日股票池 — 返回 StockPoolItem[] 数组
   */
  async getPool(): Promise<StockPoolItem[]> {
    const res = await api.get("/trade/pool");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/strategy/backtest-results
   * 回测结果 — 返回 BacktestResultItem[] 数组
   */
  async getBacktestResults(): Promise<BacktestResultItem[]> {
    const res = await api.get("/strategy/backtest-results");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * POST /api/v1/strategy/scan
   * 触发股票池扫描 — 拉取K线+评分+入库
   */
  async scan(): Promise<{ message: string; data?: any }> {
    const res = await api.post("/strategy/scan");
    const d = res.data;
    if (d && d.data) return { message: d.message, data: d.data };
    return { message: "扫描完成" };
  },
};
