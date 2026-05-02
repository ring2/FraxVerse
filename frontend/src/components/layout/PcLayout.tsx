import { useState } from "react";
import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { colors, spacing } from "../../theme/colors";

const { Content } = Layout;

const PcLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout style={{ minHeight: "100vh", background: colors.bg }}>
      <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />
      <Layout
        style={{
          marginLeft: collapsed ? 80 : spacing.sidebar,
          transition: "margin-left 0.2s",
          background: colors.bg,
        }}
      >
        <Header
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
        />
        <Content
          style={{
            marginTop: spacing.header,
            padding: 24,
            minHeight: `calc(100vh - ${spacing.header}px)`,
            overflow: "auto",
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default PcLayout;
