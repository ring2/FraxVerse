import { useState } from "react";
import { Card, Tag, Button, Radio, Divider, Space, message } from "antd";
import {
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  InfoCircleOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { colors } from "../../theme/colors";
import { useAuthStore } from "../../stores/useAuthStore";
import type { TradeMode } from "../../types/trade";

function MobileSettings() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [tradeMode, setTradeMode] = useState<TradeMode>("SIMULATION");

  const handleLogout = async () => {
    await logout();
    message.success("已退出登录");
    navigate("/login");
  };

  const handleModeChange = (e: any) => {
    const newMode = e.target.value as TradeMode;
    setTradeMode(newMode);
    message.success(`交易模式已切换为: ${newMode}`);
  };

  const modeTagColor = (mode: TradeMode) => {
    switch (mode) {
      case "LIVE":
        return colors.danger;
      case "PAPER":
        return colors.amber;
      case "SIMULATION":
        return colors.shard;
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
        bodyStyle={{ padding: 14 }}
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
        bodyStyle={{ padding: 14 }}
      >
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
            color={modeTagColor(tradeMode)}
            style={{ fontSize: 10, borderRadius: 12, fontWeight: 600 }}
          >
            {tradeMode}
          </Tag>
        </div>
        <Radio.Group
          value={tradeMode}
          onChange={handleModeChange}
          style={{ width: "100%" }}
        >
          <Space direction="vertical" style={{ width: "100%" }}>
            <Radio
              value="SIMULATION"
              style={{
                color: tradeMode === "SIMULATION" ? colors.shard : colors.muted,
                fontSize: 13,
              }}
            >
              <span style={{ marginLeft: 4 }}>SIMULATION — 模拟回测</span>
            </Radio>
            <Radio
              value="PAPER"
              style={{
                color: tradeMode === "PAPER" ? colors.amber : colors.muted,
                fontSize: 13,
              }}
            >
              <span style={{ marginLeft: 4 }}>PAPER — 纸上交易</span>
            </Radio>
            <Radio
              value="LIVE"
              style={{
                color: tradeMode === "LIVE" ? colors.danger : colors.muted,
                fontSize: 13,
              }}
            >
              <span style={{ marginLeft: 4 }}>LIVE — 实盘交易</span>
            </Radio>
          </Space>
        </Radio.Group>
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
        bodyStyle={{ padding: "12px 0" }}
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
