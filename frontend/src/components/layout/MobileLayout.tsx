import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  CompassOutlined,
  AppstoreOutlined,
  SwapOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const TAB_ITEMS = [
  { key: "/m/dashboard", title: "看盘", icon: <CompassOutlined /> },
  { key: "/m/stock-pool", title: "股票池", icon: <AppstoreOutlined /> },
  { key: "/m/trade", title: "交易", icon: <SwapOutlined /> },
  { key: "/m/settings", title: "设置", icon: <SettingOutlined /> },
];

const MobileLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        background: colors.bg,
        overflow: "hidden",
      }}
    >
      {/* Content area */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "12px 12px 0",
        }}
      >
        <Outlet />
      </div>

      {/* Bottom tab bar */}
      <div
        style={{
          display: "flex",
          background: "rgba(6, 6, 15, 0.95)",
          borderTop: `1px solid ${colors.border}`,
          paddingBottom: "env(safe-area-inset-bottom, 0)",
          flexShrink: 0,
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
                color: isActive ? colors.nebula : colors.muted,
                fontSize: 10,
                transition: "color 0.2s",
                userSelect: "none",
              }}
            >
              <span style={{ fontSize: 20, marginBottom: 2 }}>
                {item.icon}
              </span>
              <span>{item.title}</span>
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    width: 24,
                    height: 2,
                    background: colors.nebula,
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
