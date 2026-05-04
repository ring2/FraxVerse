import { useState } from "react";
import { useTheme } from "../../../theme/ThemeContext";
import { CONFIG_HELP } from "./ConfigHelp";

export default function InfoTip({ configKey }: { configKey: string }) {
  const { colors, mode } = useTheme();
  const [show, setShow] = useState(false);
  const help = CONFIG_HELP[configKey];

  if (!help) return null;

  return (
    <span style={{ position: "relative", display: "inline-flex", marginLeft: 4 }}>
      <span
        onClick={(e) => {
          e.stopPropagation();
          setShow(!show);
        }}
        style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 16, height: 16, borderRadius: "50%",
          background: colors.border.light, color: colors.text.tertiary,
          fontSize: 10, fontWeight: 700, cursor: "pointer",
          lineHeight: 1, userSelect: "none", flexShrink: 0,
        }}
      >?</span>
      {show && (
        <>
          <div onClick={(e) => { e.stopPropagation(); setShow(false); }}
            style={{ position: "fixed", inset: 0, zIndex: 999, background: "transparent" }} />
          <div style={{
            position: "absolute", top: 20, left: -8, zIndex: 1000,
            width: 240, maxWidth: "85vw",
            background: mode === "dark" ? "#2a2a2e" : "#fff",
            border: `1px solid ${colors.border.medium}`,
            borderRadius: `${colors.radius.md}px`,
            padding: "10px 12px", boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            fontSize: 11, lineHeight: 1.5, color: colors.text.primary,
          }}>
            <div style={{ marginBottom: 6 }}>{help.scene}</div>
            {help.detail && (
              <div style={{ color: colors.text.secondary, marginBottom: 4, fontSize: 10 }}>
                {help.detail}
              </div>
            )}
            <div style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 10, color: colors.text.tertiary }}>
              {help.defaultVal && <span>默认值: {help.defaultVal}</span>}
              {help.recommend && <span>推荐: {help.recommend}</span>}
            </div>
          </div>
        </>
      )}
    </span>
  );
}
