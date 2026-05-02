import { Layout, Button, Space, Tag, Dropdown } from "antd";
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/useAuthStore";
import { colors, spacing } from "../../theme/colors";

const { Header: AntHeader } = Layout;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const dropdownItems = {
    items: [
      {
        key: "settings",
        icon: <SettingOutlined />,
        label: "设置",
        onClick: () => navigate("/settings"),
      },
      { type: "divider" as const },
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        danger: true,
        onClick: handleLogout,
      },
    ],
  };

  return (
    <AntHeader
      style={{
        background: colors.surface,
        borderBottom: `1px solid ${colors.border}`,
        padding: "0 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: spacing.header,
        position: "fixed",
        top: 0,
        right: 0,
        left: collapsed ? 80 : spacing.sidebar,
        zIndex: 99,
        transition: "left 0.2s",
      }}
    >
      <Button
        type="text"
        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={onToggle}
        style={{ color: colors.muted }}
      />

      <Space>
        <Tag color="default" style={{ borderRadius: 12, borderColor: colors.border }}>
          SIMULATION
        </Tag>
        <Dropdown menu={dropdownItems} placement="bottomRight">
          <Button
            type="text"
            icon={<UserOutlined />}
            style={{ color: colors.text }}
          >
            {user?.username || "用户"}
          </Button>
        </Dropdown>
      </Space>
    </AntHeader>
  );
};

export default Header;
