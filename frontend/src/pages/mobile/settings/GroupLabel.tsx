import { useTheme } from "../../../theme/ThemeContext";

export default function GroupLabel({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: colors.text.tertiary,
      textTransform: "uppercase", letterSpacing: "0.05em",
      margin: "16px 0 8px", paddingLeft: 2,
    }}>
      {label}
    </div>
  );
}
