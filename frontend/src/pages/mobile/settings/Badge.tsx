import { useTheme } from "../../../theme/ThemeContext";

export default function Badge({ label, color }: { label: string; color?: string }) {
  const { colors } = useTheme();
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", fontSize: 11, fontWeight: 500,
      padding: "2px 10px", borderRadius: 20,
      backgroundColor: color ? `${color}18` : colors.purple[50],
      color: color || colors.purple[500], lineHeight: 1.3,
    }}>
      {label}
    </span>
  );
}
