import { useNavigate } from "react-router-dom";
import { useTheme } from "../../theme/ThemeContext";
import {
  RobotOutlined,
  ReadOutlined,
  BellOutlined,
  NodeIndexOutlined,
  EyeOutlined,
  DashboardOutlined,
  AppstoreAddOutlined,
} from "@ant-design/icons";

interface MoreEntry {
  key: string;
  title: string;
  path: string;
  icon: React.ReactNode;
  gradient: string;
}

const ENTRIES: MoreEntry[] = [
  {
    key: "ai",
    title: "AI分析",
    path: "/m/ai",
    icon: <RobotOutlined />,
    gradient: "linear-gradient(135deg, #7F77DD, #5F56C8)",
  },
  {
    key: "experience",
    title: "经验库",
    path: "/m/experience",
    icon: <ReadOutlined />,
    gradient: "linear-gradient(135deg, #E8A840, #D4922A)",
  },
  {
    key: "notifications",
    title: "通知",
    path: "/m/notifications",
    icon: <BellOutlined />,
    gradient: "linear-gradient(135deg, #E8735A, #D45A40)",
  },
  {
    key: "equity",
    title: "星轨",
    path: "/m/equity",
    icon: <NodeIndexOutlined />,
    gradient: "linear-gradient(135deg, #4DB899, #389E7C)",
  },
  {
    key: "monitor",
    title: "天眼",
    path: "/m/monitor",
    icon: <EyeOutlined />,
    gradient: "linear-gradient(135deg, #9B93E4, #7F77DD)",
  },
  {
    key: "system",
    title: "系统状态",
    path: "/m/system",
    icon: <DashboardOutlined />,
    gradient: "linear-gradient(135deg, #6B6760, #4A4742)",
  },
];

const MobileMore: React.FC = () => {
  const { colors } = useTheme();
  const navigate = useNavigate();

  return (
    <div style={{ paddingBottom: 16 }}>
      {/* Header */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: colors.text.primary,
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <AppstoreAddOutlined style={{ color: colors.purple[500] }} />
        更多功能
      </div>

      {/* 2x3 Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 16,
        }}
      >
        {ENTRIES.map((entry) => (
          <div
            key={entry.key}
            onClick={() => navigate(entry.path)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              padding: "12px 4px",
              borderRadius: colors.radius.md + "px",
              transition: "background 0.2s",
              userSelect: "none",
            }}
            onMouseDown={(e) => {
              (e.currentTarget as HTMLElement).style.background =
                colors.border.light;
            }}
            onMouseUp={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: entry.gradient,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 22,
                color: "#fff",
                boxShadow: `0 2px 8px rgba(0,0,0,0.12)`,
              }}
            >
              {entry.icon}
            </div>
            <span
              style={{
                fontSize: 12,
                color: colors.text.secondary,
                textAlign: "center",
                lineHeight: 1.3,
              }}
            >
              {entry.title}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MobileMore;
