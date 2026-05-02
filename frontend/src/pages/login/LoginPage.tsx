import { Form, Input, Button, Card, Typography, App } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/useAuthStore";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { message } = App.useApp();

  const onFinish = async (values: { username: string; password: string; remember: boolean }) => {
    setLoading(true);
    try {
      await login(values.username, values.password, values.remember);
      message.success("登录成功");
      navigate("/dashboard");
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
        background: colors.bg,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background glow */}
      <div
        style={{
          position: "absolute",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(107,92,231,0.15) 0%, transparent 70%)",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          pointerEvents: "none",
        }}
      />

      <Card
        style={{
          width: 400,
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 16,
          zIndex: 1,
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: colors.gradients.primary,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 28,
              marginBottom: 12,
            }}
          >
            ✦
          </div>
          <Title level={3} style={{ color: colors.text, margin: 0 }}>
            碎片宇宙
          </Title>
          <Text style={{ color: colors.muted, fontSize: 13 }}>
            FraxVerse · 交易修心
          </Text>
        </div>

        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: colors.muted }} />}
              placeholder="用户名"
              style={{
                background: colors.surface,
                borderColor: colors.border,
                color: colors.text,
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: colors.muted }} />}
              placeholder="密码"
              style={{
                background: colors.surface,
                borderColor: colors.border,
                color: colors.text,
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: 44, borderRadius: 8, fontSize: 16 }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: "center" }}>
          <Text style={{ color: colors.dimmed, fontSize: 12 }}>
            万千心念皆碎片，一怀内观即宇宙
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
