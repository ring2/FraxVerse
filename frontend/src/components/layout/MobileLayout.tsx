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
  const isLight = mode === "light";

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
        className="page-enter"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 12px 0",
          background: colors.bg.page,
        }}
      >
        <Outlet />
      </div>

      {/* Bottom tab bar — frosted glass */}
      <div
        style={{
          display: "flex",
          background: isLight
            ? "rgba(255,255,255,0.8)"
            : "rgba(10,10,26,0.85)",
          backdropFilter: "blur(16px) saturate(1.4)",
          WebkitBackdropFilter: "blur(16px) saturate(1.4)",
          borderTop: isLight
            ? "1px solid rgba(255,255,255,0.4)"
            : "1px solid rgba(127,119,221,0.12)",
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
                transition: "color 0.25s ease",
                userSelect: "none",
                position: "relative",
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
              {/* Active indicator dot */}
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    width: 20,
                    height: 2.5,
                    background: isLight
                      ? colors.purple[500]
                      : "linear-gradient(90deg, #7F77DD, #AFA9EC)",
                    borderRadius: "0 0 3px 3px",
                    animation: "tabIndicatorIn 0.3s ease-out",
                  }}
                />
              )}
              <span
                style={{
                  fontSize: 20,
                  marginBottom: 2,
                  lineHeight: 1,
                  transition: "transform 0.2s ease",
                }}
              >
                {item.icon}
              </span>
              <span
                style={{
                  fontSize: 10,
                  lineHeight: 1.4,
                  fontWeight: isActive ? 500 : 400,
                }}
              >
                {item.title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MobileLayout;
