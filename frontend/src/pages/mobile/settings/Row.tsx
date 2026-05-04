import InfoTip from "./InfoTip";
import { useTheme } from "../../../theme/ThemeContext";

export default function Row({
  label,
  configKey,
  desc,
  right,
}: {
  label: string;
  configKey?: string;
  desc?: string;
  right: React.ReactNode;
}) {
  const { colors } = useTheme();
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}`, gap: 12,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: colors.text.primary, lineHeight: 1.4, display: "flex", alignItems: "center" }}>
          {label}
          {configKey && <InfoTip configKey={configKey} />}
        </div>
        {desc && (
          <div style={{ fontSize: 11, color: colors.text.tertiary, marginTop: 2, lineHeight: 1.3 }}>
            {desc}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{right}</div>
    </div>
  );
}
