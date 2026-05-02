import api from "./api";
import type {
  AgentDiscussionItem,
  AgentWeightItem,
  ExperienceItem,
} from "../types/api-extended";

export const agentService = {
  /**
   * GET /api/v1/agent/discussions
   * 智能体讨论列表 — 返回 AgentDiscussionItem[] 数组
   */
  async getDiscussions(): Promise<AgentDiscussionItem[]> {
    const res = await api.get("/agent/discussions");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/agent/weights
   * 智能体权重 — 返回 AgentWeightItem[] 数组
   */
  async getWeights(): Promise<AgentWeightItem[]> {
    const res = await api.get("/agent/weights");
    return Array.isArray(res.data) ? res.data : [];
  },

  /**
   * GET /api/v1/experience/list
   * 经验列表 — 返回 ExperienceItem[] 数组
   */
  async getExperiences(): Promise<ExperienceItem[]> {
    const res = await api.get("/experience/list");
    return Array.isArray(res.data) ? res.data : [];
  },
};
