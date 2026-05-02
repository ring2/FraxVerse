import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  CompassOutlined,
  AppstoreOutlined,
  SwapOutlined,
  AppstoreAddOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../theme/ThemeContext";

const TAB_ITEMS = [
  { key: "/m/dashboard", title: "看盘", icon: <CompassOutlined /> },
  { key: "/m/stock-pool", title: "股票池", icon: <AppstoreOutlined /> },
  { key: "/m/trade", title: "交易", icon: <SwapOutlined /> },
  { key: "/m/more", title: "更多", icon: <AppstoreAddOutlined /> },
  { key: "/m/settings", title: "设置", icon: <SettingOutlined /> },
];

const MobileLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { colors, mode } = useTheme();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        background: colors.bg.page,
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Content area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 12px 0",
          background: colors.bg.page,
        }}
      >
        <Outlet />
      </div>

      {/* Bottom tab bar */}
      <div
        style={{
          display: "flex",
          background: mode === "dark" ? colors.bg.sidebar : colors.bg.surface,
          borderTop: `1px solid ${colors.border.light}`,
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
          flexShrink: 0,
          height: `calc(56px + env(safe-area-inset-bottom, 0px))`,
          position: "relative",
          zIndex: 100,
        }}
      >
        {TAB_ITEMS.map((item) => {
          const isActive = location.pathname === item.key;
          return (
            <div
              key={item.key}
              onClick={() => navigate(item.key)}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "8px 0 6px",
                cursor: "pointer",
                color: isActive ? colors.purple[500] : colors.text.tertiary,
                fontSize: 10,
                transition: "color 0.2s, opacity 0.1s",
                userSelect: "none",
                position: "relative",
                opacity: 1,
              }}
              onMouseDown={(e) => {
                (e.currentTarget as HTMLElement).style.opacity = "0.5";
              }}
              onMouseUp={(e) => {
                (e.currentTarget as HTMLElement).style.opacity = "1";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.opacity = "1";
              }}
            >
              <span style={{ fontSize: 20, marginBottom: 2, lineHeight: 1 }}>
                {item.icon}
              </span>
              <span style={{ fontSize: 10, lineHeight: 1.4 }}>{item.title}</span>
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    width: 24,
                    height: 2,
                    background: colors.purple[500],
                    borderRadius: 1,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MobileLayout;
