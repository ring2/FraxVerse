import { useTheme } from "../../../theme/ThemeContext";

export default function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  const { colors } = useTheme();
  return (
    <div
      onClick={(e) => { e.stopPropagation(); onChange(!checked); }}
      style={{
        width: 40, height: 22, borderRadius: 11,
        background: checked ? colors.purple[500] : colors.border.medium,
        position: "relative", cursor: "pointer",
        transition: "background 0.2s ease", flexShrink: 0,
      }}
    >
      <div style={{
        width: 18, height: 18, borderRadius: "50%", background: "#fff",
        position: "absolute", top: 2, left: checked ? 20 : 2,
        transition: "left 0.2s ease", boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
      }} />
    </div>
  );
}
