import { Select } from "antd";
import InfoTip from "./InfoTip";
import type { SettingsMap, LLMProvider } from "../../../services/settingsService";

const CUSTOM_MODEL_VALUE = "__custom__";

export default function UsageSlot({
  title, desc, providerKey, modelKey, reuseKey,
  connections, allProviders, configs, setConfig, colors,
}: {
  title: string;
  desc: string;
  providerKey: string;
  modelKey: string;
  reuseKey?: string;
  connections: string[];
  allProviders: LLMProvider[];
  configs: SettingsMap;
  setConfig: (key: string, value: string | number | boolean) => void;
  colors: Record<string, any>;
}) {
  const currentProvider = String(configs[providerKey] ?? "");
  const currentModel = String(configs[modelKey] ?? "");
  const currentReuse = String(configs[reuseKey ? reuseKey + "_reuse" : ""] ?? "false");
  const selectedProviderInfo = allProviders.find((p) => p.name === currentProvider);
  const availableModels = selectedProviderInfo?.models ?? [];
  const isCustomModel = currentModel && !availableModels.includes(currentModel);

  const handleProviderChange = (newProvider: string) => {
    setConfig(providerKey, newProvider);
    const info = allProviders.find((p) => p.name === newProvider);
    if (info?.default_model) setConfig(modelKey, info.default_model);
  };

  const providerOptions = allProviders.map((p) => ({
    value: p.name,
    label: p.label + (connections.includes(p.name) ? "" : "（未配 Key）"),
    disabled: !connections.includes(p.name) && p.name !== currentProvider,
  }));

  return (
    <div style={{ padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}` }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary, marginBottom: 4 }}>
        {title}
        <InfoTip configKey={providerKey.replace("_provider", "")} />
      </div>
      <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 8 }}>{desc}</div>

      {reuseKey && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <input type="checkbox" checked={currentReuse === "true"}
            onChange={() => setConfig(reuseKey + "_reuse", currentReuse === "true" ? "false" : "true")}
            style={{ cursor: "pointer" }} />
          <span style={{ fontSize: 11, color: colors.text.secondary }}>
            复用「{reuseKey === "daily_analysis" ? "每日分析" : reuseKey}」模型的配置
          </span>
        </div>
      )}

      {currentReuse !== "true" && (
        <>
          <Select showSearch style={{ width: "100%", fontSize: 12, marginBottom: 6 }}
            value={currentProvider || undefined} onChange={handleProviderChange}
            placeholder="选择厂商" options={providerOptions} />
          {currentProvider && (
            <Select showSearch style={{ width: "100%", fontSize: 12 }}
              value={isCustomModel ? CUSTOM_MODEL_VALUE : (currentModel || undefined)}
              onChange={(value: string) => setConfig(modelKey, value === CUSTOM_MODEL_VALUE ? "" : value)}
              placeholder="选择模型"
              options={[
                ...availableModels.map((m: string) => ({ value: m, label: m })),
                { value: CUSTOM_MODEL_VALUE, label: "✏️ 自定义模型" },
              ]} />
          )}
          {isCustomModel && (
            <input value={currentModel} onChange={(e) => setConfig(modelKey, e.target.value)}
              placeholder="输入自定义模型名"
              style={{ width: "100%", marginTop: 6, padding: "5px 8px", fontSize: 12,
                borderRadius: `${colors.radius.sm}px`, border: `1px solid ${colors.border.medium}`,
                background: colors.bg.surface, outline: "none", color: colors.text.primary,
                boxSizing: "border-box" }} />
          )}
          {isCustomModel && (
            <div style={{ marginTop: 4, fontSize: 11, color: colors.semantic.amber }}>
              自定义模型名，请确保该模型名在所选厂商的API中有效
            </div>
          )}
        </>
      )}
    </div>
  );
}
