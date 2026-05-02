import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  FundOutlined,
  SwapOutlined,
  LineChartOutlined,
  ExperimentOutlined,
  MessageOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  HistoryOutlined,
  NotificationOutlined,
  BookOutlined,
  AreaChartOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { colors, spacing } from "../../theme/colors";

const { Sider } = Layout;

interface SidebarProps {
  collapsed: boolean;
  onCollapse: (collapsed: boolean) => void;
}

interface NavItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", label: "宇宙总览", icon: <DashboardOutlined />, path: "/dashboard" },
  { key: "account", label: "资产星盘", icon: <AreaChartOutlined />, path: "/account" },
  { key: "stock-pool", label: "碎片候选", icon: <FundOutlined />, path: "/stock-pool" },
  { key: "agent-discussion", label: "碎片聚合", icon: <MessageOutlined />, path: "/agent-discussion" },
  { key: "trade", label: "交易星图", icon: <SwapOutlined />, path: "/trade" },
  { key: "kline", label: "K线星象", icon: <LineChartOutlined />, path: "/kline-signal" },
  { key: "backtest", label: "回测时光", icon: <ExperimentOutlined />, path: "/backtest" },
  { key: "strategy-perf", label: "修行日记", icon: <HistoryOutlined />, path: "/strategy-perf" },
  { key: "experience", label: "内观", icon: <BookOutlined />, path: "/experience" },
  { key: "notification", label: "回音", icon: <NotificationOutlined />, path: "/notification" },
  { key: "system-health", label: "系统脉搏", icon: <SafetyCertificateOutlined />, path: "/system-health" },
  { key: "settings", label: "内观设置", icon: <SettingOutlined />, path: "/settings" },
];

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onCollapse }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = navItems.find(
    (item) => item.path === location.pathname
  )?.key || "dashboard";

  const handleClick = (item: NavItem) => {
    navigate(item.path);
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      width={spacing.sidebar}
      style={{
        background: colors.surface,
        borderRight: `1px solid ${colors.border}`,
        overflow: "auto",
        height: "100vh",
        position: "fixed",
        left: 0,
        top: 0,
        zIndex: 100,
      }}
      trigger={null}
    >
      {/* Logo */}
      <div
        style={{
          height: spacing.header,
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          padding: collapsed ? 0 : "0 20px",
          borderBottom: `1px solid ${colors.border}`,
          cursor: "pointer",
        }}
        onClick={() => navigate("/dashboard")}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: colors.gradients.primary,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
            flexShrink: 0,
          }}
        >
          ✦
        </div>
        {!collapsed && (
          <span
            style={{
              marginLeft: 10,
              fontSize: 16,
              fontWeight: 600,
              color: colors.text,
              whiteSpace: "nowrap",
            }}
          >
            碎片宇宙
          </span>
        )}
      </div>

      {/* Navigation */}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        style={{
          marginTop: 8,
          border: "none",
        }}
        items={navItems.map((item) => ({
          key: item.key,
          icon: item.icon,
          label: item.label,
          onClick: () => handleClick(item),
        }))}
      />
    </Sider>
  );
};

export default Sidebar;
