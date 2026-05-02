import { Form, Input, Button, Card, Typography, App } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/useAuthStore";
import { detectDevice } from "../../utils/deviceDetect";
import { useTheme } from "../../theme/ThemeContext";
import StardustCanvas from "./StardustCanvas";
import RippleCanvas from "./RippleCanvas";

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
  const { colors, mode } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(t);
  }, []);

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

  const isLight = mode === "light";

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
      {/* Particle backdrop */}
      <StardustCanvas />

      {/* Ambient floating orbs */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${colors.purple[400]}25 0%, transparent 70%)`,
          top: "10%",
          right: "-15%",
          pointerEvents: "none",
          animation: mounted ? "driftOrb 12s ease-in-out infinite alternate" : "none",
          zIndex: 1,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 350,
          height: 350,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${isLight ? "#E8A840" : "#F0C040"}15 0%, transparent 70%)`,
          bottom: "5%",
          left: "-10%",
          pointerEvents: "none",
          animation: mounted ? "driftOrb2 10s ease-in-out infinite alternate" : "none",
          zIndex: 1,
        }}
      />

      {/* Login Card */}
      <div
        style={{
          width: 420,
          maxWidth: "100%",
          zIndex: 2,
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)",
          transition: "opacity 0.6s ease-out, transform 0.6s ease-out",
        }}
      >
        <Card
          style={{
            width: "100%",
            background: isLight
              ? "rgba(255,255,255,0.72)"
              : "rgba(18,18,42,0.75)",
            backdropFilter: "blur(24px) saturate(1.4)",
            WebkitBackdropFilter: "blur(24px) saturate(1.4)",
            border: isLight
              ? "1px solid rgba(255,255,255,0.5)"
              : "1px solid rgba(127,119,221,0.2)",
            borderRadius: 24,
            boxShadow: isLight
              ? "0 8px 48px rgba(0,0,0,0.04), 0 0 0 1px rgba(127,119,221,0.06)"
              : "0 8px 48px rgba(0,0,0,0.3), 0 0 0 1px rgba(127,119,221,0.08)",
            transition: "background 0.35s, box-shadow 0.35s, border-color 0.35s",
          }}
          styles={{
            body: {
              padding: "52px 44px",
              position: "relative",
              overflow: "hidden",
            } as React.CSSProperties,
          }}
        >
          {/* Top accent bar */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 3,
              background:
                "linear-gradient(90deg, transparent, #9B93E4, #7F77DD, #9B93E4, transparent)",
              borderRadius: "24px 24px 0 0",
              opacity: 0.6,
            }}
          />

          {/* Logo */}
          <div
            style={{
              textAlign: "center",
              marginBottom: 36,
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(-12px)",
              transition:
                "opacity 0.8s ease-out 0.15s, transform 0.8s ease-out 0.15s",
            }}
          >
            <div
              style={{
                position: "relative",
                width: 68,
                height: 68,
                margin: "0 auto 22px",
              }}
            >
              {/* Spinning conic glow ring */}
              <div
                style={{
                  position: "absolute",
                  inset: -8,
                  borderRadius: 18,
                  background: `conic-gradient(from 0deg, ${colors.purple[400]}66, ${colors.purple[200]}33, ${colors.purple[400]}66, ${colors.purple[500]}44, ${colors.purple[400]}66)`,
                  animation: mounted ? "spinGlow 4s linear infinite" : "none",
                  mask: "radial-gradient(ellipse at center, transparent 40%, black 60%, transparent 100%)",
                  WebkitMask:
                    "radial-gradient(ellipse at center, transparent 40%, black 60%, transparent 100%)",
                }}
              />
              <div
                style={{
                  width: 68,
                  height: 68,
                  borderRadius: 16,
                  background: colors.gradient.logo,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 28,
                  position: "relative",
                  zIndex: 1,
                  boxShadow: `0 4px 16px ${colors.purple[500]}44`,
                  animation: mounted ? "breatheGlow 3s ease-in-out infinite" : "none",
                }}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="32"
                  height="32"
                >
                  <circle cx="12" cy="12" r="2.5" fill="white" />
                  <ellipse cx="12" cy="12" rx="10" ry="4" stroke="rgba(255,255,255,0.5)" />
                  <ellipse cx="12" cy="12" rx="10" ry="4" stroke="rgba(255,255,255,0.25)" transform="rotate(60 12 12)" />
                </svg>
              </div>
            </div>
            <Title
              level={3}
              style={{
                color: colors.text.primary,
                margin: 0,
                fontSize: 24,
                fontWeight: 600,
                letterSpacing: "0.02em",
              }}
            >
              FraxVerse
            </Title>
            <Text
              style={{
                color: colors.text.tertiary,
                fontSize: 13,
                letterSpacing: "0.04em",
              }}
            >
              碎片宇宙 · 智能量化交易系统
            </Text>
          </div>

          {/* Form */}
          <div
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(10px)",
              transition:
                "opacity 0.8s ease-out 0.3s, transform 0.8s ease-out 0.3s",
            }}
          >
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
                  className="frax-input"
                  style={{
                    background: isLight
                      ? "rgba(250,249,247,0.8)"
                      : "rgba(6,6,15,0.5)",
                    color: colors.text.primary,
                    borderRadius: 12,
                    fontFamily: "inherit",
                    padding: "11px 14px",
                    transition: "all 0.25s ease",
                    boxShadow: "inset 0 1px 3px rgba(0,0,0,0.03)",
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
                  className="frax-input"
                  style={{
                    background: isLight
                      ? "rgba(250,249,247,0.8)"
                      : "rgba(6,6,15,0.5)",
                    color: colors.text.primary,
                    borderRadius: 12,
                    fontFamily: "inherit",
                    padding: "11px 14px",
                    transition: "all 0.25s ease",
                    boxShadow: "inset 0 1px 3px rgba(0,0,0,0.03)",
                  }}
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 12 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  className="frax-btn"
                  style={{
                    height: 48,
                    borderRadius: 12,
                    fontSize: 15,
                    fontWeight: 600,
                    background: colors.gradient.primary,
                    border: "none",
                    letterSpacing: 3,
                    boxShadow: colors.btnShadow,
                    transition: "all 0.25s ease",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  登 录
                </Button>
              </Form.Item>
            </Form>

            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text
                style={{
                  fontSize: 12,
                  background:
                    "linear-gradient(135deg, #9B93E4, #E8A840, #7F77DD)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  fontWeight: 500,
                  letterSpacing: "0.06em",
                }}
              >
                万千心念皆碎片，一怀内观即宇宙
              </Text>
            </div>
          </div>
        </Card>
      </div>

      {/* Ripple / fragment click effect */}
      <RippleCanvas />
    </div>
  );
};

export default LoginPage;
