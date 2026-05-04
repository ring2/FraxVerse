import { useState } from "react";

export default function ConnectionCard({
  provider, connection, onSave, onDelete, colors,
}: {
  provider: { name: string; label: string; default_base_url: string };
  connection?: { has_api_key: boolean; base_url: string };
  onSave: (providerName: string, apiKey: string, baseUrl: string) => void;
  onDelete: (providerName: string) => void;
  colors: Record<string, any>;
}) {
  const [apiKey, setApiKey] = useState(connection?.has_api_key ? "••••••••" : "");
  const [baseUrl, setBaseUrl] = useState(connection?.base_url ?? "");
  const [changed, setChanged] = useState(false);

  const handleSave = () => {
    onSave(provider.name, apiKey === "••••••••" ? "" : apiKey, baseUrl);
    setChanged(false);
  };

  return (
    <div style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border.light}` }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: colors.text.primary }}>{provider.label}</span>
        {connection ? (
          <span onClick={() => onDelete(provider.name)}
            style={{ fontSize: 10, color: colors.semantic.down, cursor: "pointer" }}>删除</span>
        ) : (
          <span style={{ fontSize: 10, color: colors.text.tertiary }}>未配置</span>
        )}
      </div>
      <div style={{ display: "flex", gap: 4, alignItems: "center", marginBottom: 4 }}>
        <input value={apiKey} onChange={(e) => { setApiKey(e.target.value); setChanged(true); }}
          placeholder="API Key" type="password"
          style={{ flex: 1, padding: "4px 6px", fontSize: 11,
            borderRadius: `${colors.radius.sm}px`, border: `1px solid ${colors.border.medium}`,
            background: colors.bg.surface, outline: "none", color: colors.text.primary }} />
        <span style={{ fontSize: 10, color: colors.text.tertiary, whiteSpace: "nowrap" }}>Key</span>
      </div>
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        <input value={baseUrl} onChange={(e) => { setBaseUrl(e.target.value); setChanged(true); }}
          placeholder={provider.default_base_url}
          style={{ flex: 1, padding: "4px 6px", fontSize: 11,
            borderRadius: `${colors.radius.sm}px`, border: `1px solid ${colors.border.medium}`,
            background: colors.bg.surface, outline: "none", color: colors.text.primary }} />
        <span style={{ fontSize: 10, color: colors.text.tertiary, whiteSpace: "nowrap" }}>URL</span>
        {changed && (
          <button onClick={handleSave}
            style={{ padding: "3px 8px", fontSize: 10, borderRadius: `${colors.radius.sm}px`,
              border: "none", background: colors.purple[500], color: "#fff", cursor: "pointer", lineHeight: 1.3 }}>
            保存</button>
        )}
      </div>
    </div>
  );
}
