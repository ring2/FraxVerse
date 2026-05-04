import { useState } from "react";
import { useTheme } from "../../../theme/ThemeContext";

export default function CollapseCard({
  dotColor, title, subtitle, defaultOpen = false,
  totalItems, configuredItems, children,
}: {
  dotColor?: string;
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  totalItems?: number;
  configuredItems?: number;
  children: React.ReactNode;
}) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{
      background: colors.bg.surface, borderRadius: `${colors.radius.md}px`,
      border: `1px solid ${colors.border.light}`, overflow: "hidden", marginBottom: 10,
    }}>
      <div onClick={() => setOpen(!open)} style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 14px", cursor: "pointer", userSelect: "none",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: dotColor || colors.purple[400], flexShrink: 0,
          }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>
              {title}
            </span>
            {subtitle && (
              <div style={{
                fontSize: 10, color: colors.text.tertiary, marginTop: 1, lineHeight: 1.3,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {subtitle}
              </div>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {totalItems !== undefined && (
            <span style={{ fontSize: 10, color: colors.text.tertiary, whiteSpace: "nowrap" }}>
              {configuredItems}/{totalItems}
            </span>
          )}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke={colors.text.tertiary} strokeWidth="2" strokeLinecap="round"
            style={{
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease", flexShrink: 0,
            }}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
      {open && <div style={{ paddingBottom: 4 }}>{children}</div>}
    </div>
  );
}
