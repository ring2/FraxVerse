import { useTheme } from "../../../theme/ThemeContext";

export default function InputField({
  value, onChange, placeholder, type = "text", suffix,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  suffix?: string;
}) {
  const { colors } = useTheme();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 90, padding: "6px 8px", borderRadius: `${colors.radius.sm}px`,
          border: `1px solid ${colors.border.medium}`, background: colors.bg.surface,
          outline: "none", color: colors.text.primary, fontSize: 12,
          textAlign: type === "number" ? "center" : "left", lineHeight: 1.4,
        }}
      />
      {suffix && (
        <span style={{ fontSize: 11, color: colors.text.tertiary, whiteSpace: "nowrap" }}>
          {suffix}
        </span>
      )}
    </div>
  );
}
