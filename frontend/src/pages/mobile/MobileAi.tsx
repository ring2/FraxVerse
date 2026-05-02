import { useTheme } from "../../theme/ThemeContext";
import { RobotOutlined } from "@ant-design/icons";

const MobileAi: React.FC = () => {
  const { colors } = useTheme();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        gap: 12,
      }}
    >
      <RobotOutlined
        style={{ fontSize: 48, color: colors.purple[400], opacity: 0.6 }}
      />
      <div
        style={{
          fontSize: 16,
          fontWeight: 600,
          color: colors.text.secondary,
        }}
      >
        AI 分析
      </div>
      <div
        style={{
          fontSize: 13,
          color: colors.text.tertiary,
        }}
      >
        开发中
      </div>
    </div>
  );
};

export default MobileAi;
