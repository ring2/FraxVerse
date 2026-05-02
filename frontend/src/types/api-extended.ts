/**
 * FraxVerse · 前端补充类型
 *
 * 后端 OpenAPI schema 没有覆盖的类型放在这里。
 * 所有从后端 API 返回的类型统一用 api-generated.ts 的 components["schemas"]。
 * 只有前端独有的、JWT decode 出的、或 UI 专用的类型写在此文件。
 */
import type { components } from "./api-generated";

// ---- Auth / User ----

/** 用户信息——仅从 JWT decode 获得，后端没有返回 user 的独立 API */
export interface User {
  id: number;
  username: string;
  created_at: string;
}

// ---- API Wrapper ----

/** API 统一响应包装——后端不返回这个，是前端 axios 拦截器层加的 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ---- Re-export commonly used backend schemas for convenience ----

export type LoginRequest = components["schemas"]["LoginRequest"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type SystemInitStatus = components["schemas"]["SystemInitStatus"];
export type SetupRequest = components["schemas"]["SetupRequest"];
export type PortfolioSummary = components["schemas"]["PortfolioSummary"];
export type PositionItem = components["schemas"]["PositionItem"];
export type OrderResponse = components["schemas"]["OrderResponse"];
export type OrderCreateRequest = components["schemas"]["OrderCreateRequest"];
export type StockPoolItem = components["schemas"]["StockPoolItem"];
export type MarketStateResponse = components["schemas"]["MarketStateResponse"];
export type KlineItem = components["schemas"]["KlineItem"];
export type SectorItem = components["schemas"]["SectorItem"];
export type NewsItem = components["schemas"]["NewsItem"];
export type AgentDiscussionItem = components["schemas"]["AgentDiscussionItem"];
export type AgentWeightItem = components["schemas"]["AgentWeightItem"];
export type BacktestResultItem = components["schemas"]["BacktestResultItem"];
export type ExperienceItem = components["schemas"]["ExperienceItem"];
export type NotificationItem = components["schemas"]["NotificationItem"];
export type RiskEventItem = components["schemas"]["RiskEventItem"];
export type RiskMetricsItem = components["schemas"]["RiskMetricsItem"];
export type ServiceStatus = components["schemas"]["ServiceStatus"];
export type SystemResource = components["schemas"]["SystemResource"];
export type TradeModeResponse = components["schemas"]["TradeModeResponse"];
