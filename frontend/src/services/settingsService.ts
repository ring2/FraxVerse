import api from "./api";

export interface SettingsMap {
  [key: string]: string | number | boolean;
}

async function getConfigs(): Promise<SettingsMap> {
  const res = await api.get<Record<string, string | number | boolean>>("/settings/configs");
  return res.data ?? {};
}

async function updateConfigs(configs: SettingsMap): Promise<void> {
  await api.put("/settings/configs", configs);
}

export const settingsService = { getConfigs, updateConfigs };
