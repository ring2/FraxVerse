import api from "./api";

export interface SettingsMap {
  [key: string]: string | number | boolean;
}

export interface LLMProvider {
  name: string;
  label: string;
  default_base_url: string;
  api_format: string;
  models: string[];
  default_model: string;
}

export interface LLMConnection {
  provider_name: string;
  label: string;
  has_api_key: boolean;
  base_url: string;
}

export interface TradeModeInfo {
  current_mode: string;
  confirm_mode: string;
  emergency_stop: boolean;
}

async function getConfigs(): Promise<SettingsMap> {
  const res = await api.get<Record<string, string | number | boolean>>("/settings/configs");
  return res.data ?? {};
}

async function updateConfigs(configs: SettingsMap): Promise<void> {
  await api.put("/settings/configs", configs);
}

async function getLLMProviders(): Promise<LLMProvider[]> {
  const res = await api.get<LLMProvider[]>("/settings/llm-providers");
  return res.data ?? [];
}

/* ─── 厂商连接管理 ─── */

async function getLLMConnections(): Promise<LLMConnection[]> {
  const res = await api.get<{ connections: LLMConnection[] }>("/settings/llm-connections");
  return res.data?.connections ?? [];
}

async function upsertLLMConnection(
  provider_name: string,
  api_key: string,
  base_url?: string,
  label?: string,
): Promise<LLMConnection> {
  const res = await api.put<LLMConnection>("/settings/llm-connections", {
    provider_name,
    api_key,
    base_url: base_url ?? "",
    label: label ?? "",
  });
  return res.data;
}

async function deleteLLMConnection(provider_name: string): Promise<void> {
  await api.delete(`/settings/llm-connections/${provider_name}`);
}

/* ─── 交易模式 ─── */

async function getTradeMode(): Promise<TradeModeInfo> {
  const res = await api.get<TradeModeInfo>("/trade/mode");
  return res.data;
}

async function updateTradeMode(
  target_mode?: string,
  confirm_mode?: string,
): Promise<void> {
  await api.post("/trade/mode", {
    ...(target_mode ? { target_mode } : {}),
    ...(confirm_mode ? { confirm_mode } : {}),
  });
}

export const settingsService = {
  getConfigs,
  updateConfigs,
  getLLMProviders,
  getLLMConnections,
  upsertLLMConnection,
  deleteLLMConnection,
  getTradeMode,
  updateTradeMode,
};
