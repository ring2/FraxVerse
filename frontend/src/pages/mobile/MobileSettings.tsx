import { useEffect, useState } from "react";
import { Card, Tag, Button, Radio, Divider, Space, Spin, App } from "antd";
import {
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  InfoCircleOutlined,
  StarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { colors } from "../../theme/colors";
import { useAuthStore } from "../../stores/useAuthStore";
import { tradeService } from "../../services/tradeService";
import { monitorService } from "../../services/monitorService";
import type { TradeModeResponse, ServiceStatus } from "../../types/api-extended";

function MobileSettings() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const [loadingMode, setLoadingMode] = useState(true);
  const [loadingServices, setLoadingServices] = useState(true);
  const [tradeMode, setTradeMode] = useState<TradeModeResponse | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      tradeService.getMode(),
      monitorService.getServices(),
    ])
      .then(([tm, svc]) => {
        if (cancelled) return;
        setTradeMode(tm);
        setServices(svc);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load settings data:", err);
        message.error("加载设置数据失败");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingMode(false);
          setLoadingServices(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const handleLogout = async () => {
    await logout();
    message.success("已退出登录");
    navigate("/login");
  };

  const handleModeChange = async (e: any) => {
    const newMode = e.target.value;
    setUpdating(true);
    try {
      const updated = await tradeService.updateMode({ target_mode: newMode });
      if (updated) {
        setTradeMode(updated);
      }
      message.success(`交易模式已切换为: ${newMode}`);
    } catch (err: any) {
      console.error("Failed to update trade mode:", err);
      message.error(err?.response?.data?.message || "切换交易模式失败");
    } finally {
      setUpdating(false);
    }
  };

  const currentMode = tradeMode?.current_mode ?? "SIMULATION";

  const modeTagColor = (mode: string) => {
    switch (mode) {
      case "LIVE":
        return colors.danger;
      case "PAPER":
        return colors.amber;
      case "SIMULATION":
        return colors.shard;
      default:
        return colors.muted;
    }
  };

  return (
    <div style={{ paddingBottom: 16 }}>
      {/* Header */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: colors.text,
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <SettingOutlined style={{ color: colors.nebula }} />
        设置
      </div>

      {/* Profile Card */}
      <Card
        size="small"
        style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          marginBottom: 10,
        }}
        styles={{ body: { padding: 14 } }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 20,
              background: colors.gradients.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              color: "#fff",
              fontWeight: 700,
            }}
          >
            <UserOutlined />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
              {user?.username || "FraxVerse User"}
            </div>
            <div style={{ color: colors.dimmed, fontSize: 11, marginTop: 2 }}>
              <InfoCircleOutlined style={{ marginRight: 4 }} />
              系统版本 v1.0.0
            </div>
          </div>
        </div>
      </Card>

      {/* Trade Mode */}
      <Card
        size="small"
        style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          marginBottom: 10,
        }}
        styles={{ body: { padding: 14 } }}
      >
        {loadingMode ? (
          <div style={{ textAlign: "center", padding: 8 }}>
            <Spin size="small" />
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <span style={{ color: colors.text, fontSize: 13, fontWeight: 600 }}>
                交易模式
              </span>
              <Tag
                color={modeTagColor(currentMode)}
                style={{ fontSize: 10, borderRadius: 12, fontWeight: 600 }}
              >
                {currentMode}
              </Tag>
            </div>
            <Radio.Group
              value={currentMode}
              onChange={handleModeChange}
              disabled={updating}
              style={{ width: "100%" }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                <Radio
                  value="SIMULATION"
                  style={{
                    color: currentMode === "SIMULATION" ? colors.shard : colors.muted,
                    fontSize: 13,
                  }}
                >
                  <span style={{ marginLeft: 4 }}>SIMULATION — 模拟回测</span>
                </Radio>
                <Radio
                  value="PAPER"
                  style={{
                    color: currentMode === "PAPER" ? colors.amber : colors.muted,
                    fontSize: 13,
                  }}
                >
                  <span style={{ marginLeft: 4 }}>PAPER — 纸上交易</span>
                </Radio>
                <Radio
                  value="LIVE"
                  style={{
                    color: currentMode === "LIVE" ? colors.danger : colors.muted,
                    fontSize: 13,
                  }}
                >
                  <span style={{ marginLeft: 4 }}>LIVE — 实盘交易</span>
                </Radio>
              </Space>
            </Radio.Group>
          </>
        )}
      </Card>

      {/* Service Status */}
      <Card
        size="small"
        style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          marginBottom: 10,
        }}
        styles={{ body: { padding: 14 } }}
      >
        <div
          style={{
            color: colors.text,
            fontSize: 13,
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          服务状态
        </div>
        {loadingServices ? (
          <div style={{ textAlign: "center", padding: 8 }}>
            <Spin size="small" />
          </div>
        ) : services.length === 0 ? (
          <div style={{ color: colors.dimmed, fontSize: 12, textAlign: "center" }}>
            暂无服务数据
          </div>
        ) : (
          <Space direction="vertical" style={{ width: "100%" }}>
            {services.map((svc, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "6px 0",
                  borderBottom:
                    idx < services.length - 1
                      ? `1px solid ${colors.border}`
                      : "none",
                }}
              >
                <span style={{ color: colors.text, fontSize: 12 }}>
                  {svc.service}
                </span>
                <span>
                  {svc.status === "healthy" ? (
                    <Tag
                      icon={<CheckCircleOutlined />}
                      color="success"
                      style={{ fontSize: 10, borderRadius: 8, margin: 0 }}
                    >
                      {svc.status}
                    </Tag>
                  ) : (
                    <Tag
                      icon={<CloseCircleOutlined />}
                      color="error"
                      style={{ fontSize: 10, borderRadius: 8, margin: 0 }}
                    >
                      {svc.status}
                    </Tag>
                  )}
                </span>
              </div>
            ))}
          </Space>
        )}
      </Card>

      {/* Logout */}
      <Button
        danger
        size="large"
        block
        icon={<LogoutOutlined />}
        onClick={handleLogout}
        style={{
          borderRadius: 10,
          height: 44,
          fontWeight: 600,
          fontSize: 15,
          marginBottom: 20,
          borderColor: colors.danger,
          color: colors.danger,
          background: "rgba(255, 71, 87, 0.08)",
        }}
      >
        退出登录
      </Button>

      <Divider style={{ borderColor: colors.border, margin: "8px 0" }} />

      {/* Brand Info */}
      <Card
        size="small"
        style={{
          background: "transparent",
          border: "none",
          textAlign: "center",
        }}
        styles={{ body: { padding: "12px 0" } }}
      >
        <div
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: colors.nebula,
            marginBottom: 4,
          }}
        >
          <StarOutlined style={{ marginRight: 6 }} />
          FraxVerse
        </div>
        <div style={{ color: colors.dimmed, fontSize: 11, lineHeight: 1.6 }}>
          交易修心 · 心念为碎片 · 宇宙为心之投影
        </div>
      </Card>
    </div>
  );
}

export default MobileSettings;
