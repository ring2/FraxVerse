import { Form, Input, Button, Card, Typography, App } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/useAuthStore";
import { detectDevice } from "../../utils/deviceDetect";
import { useTheme } from "../../theme/ThemeContext";

const getRedirectTarget = () => {
  if (detectDevice() === "mobile") return "/m/dashboard";
  if (window.innerWidth < 768) return "/m/dashboard";
  return "/dashboard";
};

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { message } = App.useApp();
  const { colors } = useTheme();

  const onFinish = async (values: {
    username: string;
    password: string;
    remember: boolean;
  }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      const target = getRedirectTarget();
      navigate(target);
    } catch {
      message.error("用户名或密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: colors.bg.page,
        position: "relative",
        overflow: "hidden",
        padding: 16,
        transition: "background 0.35s",
      }}
    >
      {/* Background glow */}
      <div
        style={{
          position: "absolute",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${colors.purple[400]}33 0%, transparent 70%)`,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          pointerEvents: "none",
        }}
      />

      <Card
        style={{
          width: 400,
          maxWidth: "100%",
          background: colors.bg.surface,
          border: `1px solid ${colors.border.light}`,
          borderRadius: 20,
          zIndex: 1,
          transition: "background 0.35s, border-color 0.35s",
        }}
        styles={{ body: { padding: "48px 40px" } }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 14,
              background: colors.gradient.logo,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 28,
              marginBottom: 20,
              boxShadow: `0 2px 8px ${colors.purple[500]}40`,
            }}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              width="32"
              height="32"
            >
              <circle cx="12" cy="12" r="3" />
              <ellipse cx="12" cy="12" rx="9" ry="5" />
              <ellipse cx="12" cy="12" rx="9" ry="5" transform="rotate(60 12 12)" />
              <ellipse cx="12" cy="12" rx="9" ry="5" transform="rotate(120 12 12)" />
            </svg>
          </div>
          <Title
            level={3}
            style={{
              color: colors.text.primary,
              margin: 0,
              fontSize: 24,
              fontWeight: 600,
            }}
          >
            FraxVerse
          </Title>
          <Text
            style={{
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            碎片宇宙 · 智能量化交易系统
          </Text>
        </div>

        <Form
          name="login"
          initialValues={{ remember: true, username: "admin" }}
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: colors.text.tertiary }} />}
              placeholder="用户名"
              style={{
                background: colors.bg.page,
                borderColor: colors.border.medium,
                color: colors.text.primary,
                borderRadius: 10,
                fontFamily: "inherit",
                padding: "11px 14px",
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={
                <LockOutlined style={{ color: colors.text.tertiary }} />
              }
              placeholder="密码"
              style={{
                background: colors.bg.page,
                borderColor: colors.border.medium,
                color: colors.text.primary,
                borderRadius: 10,
                fontFamily: "inherit",
                padding: "11px 14px",
              }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 44,
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                background: colors.gradient.primary,
                border: "none",
                letterSpacing: 2,
              }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: "center" }}>
          <Text style={{ color: colors.text.tertiary, fontSize: 12 }}>
            万千心念皆碎片，一怀内观即宇宙
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
