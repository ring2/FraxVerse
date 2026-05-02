import api from "./api";
import type { ApiResponse } from "../types/api-extended";

// ─── Agent 讨论记录 ───────────────────────────────────────────────────────────

/**
 * Agent 讨论记录项 — 对应 GET /api/v1/agent/discussions 返回的 items
 */
export interface AgentDiscussionItemEx {
  id: number;
  date: string;
  stockCode: string;
  roundNum: number;
  agentName: string;
  score: number | null;
  buyReasons: string[];
  againstReasons: string[];
  confidence: number;
  isValid: boolean;
  predictedOutcome: string | null;
  actualOutcome: string | null;
  promptTokens: number;
  completionTokens: number;
  modelName: string | null;
  createdAt: string;
}

/**
 * Agent 权重配置项 — 对应 GET /api/v1/agent/weights 返回的 weights
 */
export interface AgentWeightItemEx {
  agentName: string;
  marketState: string;
  baseWeight: number;
  calibFactor: number;
  effectiveWeight: number;
  winRate: number;
  recentCount: number;
  extremeCount: number;
  isDegraded: boolean;
}

/**
 * 决策记录项 — 对应 GET /api/v1/agent/decisions 返回的 decisions
 */
export interface AgentDecisionItemEx {
  stockCode: string;
  totalScore: number;
  buyScoreSum: number;
  againstScoreSum: number;
  netScore: number;
  decision: string;
  decisionReason: string;
  riskVeto: boolean;
  riskVetoReason: string | null;
  convergenceRounds: number;
  convergenceMethod: string;
  agentVotes: Record<string, { score: number; weight: number; effectiveScore: number }>;
  createdAt: string;
}

/**
 * 校准面板 Agent 数据
 */
export interface CalibrationAgentItem {
  agentName: string;
  displayName: string;
  winRate: number;
  recentCount: number;
  calibFactor: number;
  history: Array<{ date: string; predicted: string; actual: string }>;
  winRateTrend: number[];
}

export const agentService = {
  /**
   * GET /api/v1/agent/discussions
   * Agent 讨论列表 — 分页返回
   */
  async getDiscussions(params?: {
    date?: string;
    stockCode?: string;
    agentName?: string;
    page?: number;
    pageSize?: number;
  }): Promise<{ items: AgentDiscussionItemEx[]; total: number; page: number; pageSize: number; totalPages: number }> {
    const res = await api.get<ApiResponse<{
      items: AgentDiscussionItemEx[];
      total: number;
      page: number;
      pageSize: number;
      totalPages: number;
    }>>("/agent/discussions", { params });
    const data = res.data?.data;
    return data ?? { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 };
  },

  /**
   * GET /api/v1/agent/discussions/{date}/{code}
   * 某日某标讨论详情
   */
  async getDiscussionDetail(date: string, code: string): Promise<{
    date: string;
    stockCode: string;
    rounds: Array<{ roundNum: number; outputs: AgentDiscussionItemEx[] }>;
  } | null> {
    const res = await api.get<ApiResponse<{ date: string; stockCode: string; rounds: Array<{ roundNum: number; outputs: AgentDiscussionItemEx[] }> }>>(`/agent/discussions/${date}/${code}`);
    return res.data?.data ?? null;
  },

  /**
   * GET /api/v1/agent/weights
   * Agent 权重配置
   */
  async getWeights(): Promise<{
    weights: AgentWeightItemEx[];
    currentMarketState: string;
  }> {
    const res = await api.get<ApiResponse<{ weights: AgentWeightItemEx[]; currentMarketState: string }>>("/agent/weights");
    return res.data?.data ?? { weights: [], currentMarketState: "mainline_confirmed" };
  },

  /**
   * PUT /api/v1/agent/weights
   * 更新基准权重
   */
  async updateWeights(weights: Array<{ agentName: string; marketState: string; baseWeight: number }>): Promise<void> {
    await api.put("/agent/weights", { weights });
  },

  /**
   * GET /api/v1/agent/decisions
   * 决策记录
   */
  async getDecisions(params?: {
    date?: string;
    page?: number;
    pageSize?: number;
  }): Promise<{ date: string; decisions: AgentDecisionItemEx[]; total: number }> {
    const res = await api.get<ApiResponse<{ date: string; decisions: AgentDecisionItemEx[]; total: number }>>("/agent/decisions", { params });
    return res.data?.data ?? { date: "", decisions: [], total: 0 };
  },

  /**
   * GET /api/v1/agent/decisions/{date}
   * 某日决策
   */
  async getDecisionsByDate(date: string): Promise<{ date: string; decisions: AgentDecisionItemEx[] }> {
    const res = await api.get<ApiResponse<{ date: string; decisions: AgentDecisionItemEx[] }>>(`/agent/decisions/${date}`);
    return res.data?.data ?? { date, decisions: [] };
  },

  /**
   * POST /api/v1/agent/trigger
   * 手动触发 Agent 分析
   */
  async triggerAnalysis(stockCodes?: string[]): Promise<{
    taskId: string;
    status: string;
    stockCount: number;
    decisions: Array<{ stockCode: string; decision: string; totalScore: number }>;
  }> {
    const res = await api.post<ApiResponse<{
      taskId: string;
      status: string;
      stockCount: number;
      decisions: Array<{ stockCode: string; decision: string; totalScore: number }>;
    }>>("/agent/trigger", { stockCodes });
    return res.data?.data ?? { taskId: "", status: "completed", stockCount: 0, decisions: [] };
  },

  /**
   * GET /api/v1/agent/calibration
   * 校准面板数据
   */
  async getCalibration(): Promise<{ agents: CalibrationAgentItem[] }> {
    const res = await api.get<ApiResponse<{ agents: CalibrationAgentItem[] }>>("/agent/calibration");
    return res.data?.data ?? { agents: [] };
  },

  /**
   * GET /api/v1/agent/llm-usage
   * LLM 用量统计
   */
  async getLlmUsage(params?: {
    startDate?: string;
    endDate?: string;
    groupBy?: "day" | "agent" | "model";
  }): Promise<{
    dailyUsage: unknown[];
    budgetStatus: {
      dailyLimit: number;
      dailyUsed: number;
      monthlyLimit: number;
      monthlyUsed: number;
      isOverBudget: boolean;
      degradeLevel: string;
    };
  }> {
    const res = await api.get("/agent/llm-usage", { params });
    return res.data?.data ?? { dailyUsage: [], budgetStatus: { dailyLimit: 100000, dailyUsed: 0, monthlyLimit: 2000000, monthlyUsed: 0, isOverBudget: false, degradeLevel: "none" } };
  },

  /**
   * GET /api/v1/agent/prompts
   * 提示词列表
   */
  async getPrompts(): Promise<{ prompts: Array<{ id: number; agentName: string; version: string; isActive: boolean; changeNote: string | null; createdAt: string }> }> {
    const res = await api.get("/agent/prompts");
    return res.data?.data ?? { prompts: [] };
  },

  /**
   * PUT /api/v1/agent/prompts/{id}/activate
   * 激活提示词版本
   */
  async activatePrompt(id: number): Promise<void> {
    await api.put(`/agent/prompts/${id}/activate`);
  },
};
