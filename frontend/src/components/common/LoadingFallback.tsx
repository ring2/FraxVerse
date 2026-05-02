import { Spin } from "antd";
import { useTheme } from "../../theme/ThemeContext";

const LoadingFallback: React.FC = () => {
  const { colors } = useTheme();
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        background: colors.bg.page,
        transition: "background 0.35s",
      }}
    >
      <Spin size="large" />
    </div>
  );
};

export default LoadingFallback;
