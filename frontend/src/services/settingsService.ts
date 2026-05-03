import api from "./api";

export interface SettingsMap {
  [key: string]: string | number | boolean;
}

export interface LLMProvider {
  name: string;
  label: string;
  base_url: string;
  api_format: string;
  models: string[];
  default_model: string;
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

export const settingsService = { getConfigs, updateConfigs, getLLMProviders };
