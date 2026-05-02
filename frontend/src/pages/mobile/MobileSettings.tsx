import { useCallback, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { useAuthStore } from "../../stores/useAuthStore";

/* ---- Toggle component ---- */
const ToggleSwitch = ({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) => {
  const { colors } = useTheme();
  return (
    <div
      onClick={() => onChange(!checked)}
      style={{
        width: 40,
        height: 22,
        borderRadius: 11,
        background: checked ? colors.purple[500] : colors.border.medium,
        position: "relative",
        cursor: "pointer",
        transition: "background 0.2s ease",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: "#fff",
          position: "absolute",
          top: 2,
          left: checked ? 20 : 2,
          transition: "left 0.2s ease",
          boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
        }}
      />
    </div>
  );
};

/* ---- Setting row component ---- */
const SettingRow = ({
  label,
  right,
}: {
  label: string;
  right: React.ReactNode;
}) => {
  const { colors } = useTheme();
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 14px",
        borderBottom: `1px solid ${colors.border.light}`,
      }}
    >
      <span
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: colors.text.primary,
          lineHeight: 1.4,
        }}
      >
        {label}
      </span>
      <div style={{ flexShrink: 0 }}>{right}</div>
    </div>
  );
};

function MobileSettings() {
  const { message } = App.useApp();
  const { colors, mode, toggle } = useTheme();
  const { user } = useAuthStore();

  /* ---- local state ---- */
  const [riskAlertOn, setRiskAlertOn] = useState(true);
  const [agentDigestOn, setAgentDigestOn] = useState(true);
  const [pushOn, setPushOn] = useState(true);

  /* ---- handlers ---- */
  const handleChangePassword = useCallback(() => {
    message.info("修改密码 — 开发中");
  }, [message]);

  const handleModeConfirm = useCallback(() => {
    message.info("确认模式切换 — 开发中");
  }, [message]);

  return (
    <div>
      {/* ===== 标题栏 ===== */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: colors.text.primary,
          marginBottom: 14,
          lineHeight: 1.3,
        }}
      >
        设置
      </div>

      {/* ===== 账号 ===== */}
      <div style={{ marginBottom: 12 }}>
        <MobileSectionCard title="账号">
          <SettingRow
            label="用户名"
            right={
              <span
                style={{
                  fontSize: 13,
                  color: colors.text.secondary,
                }}
              >
                {user?.username || "admin"}
              </span>
            }
          />
          <div style={{ padding: "10px 14px" }}>
            <button
              onClick={handleChangePassword}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                padding: "6px 14px",
                borderRadius: `${colors.radius.md}px`,
                fontSize: 13,
                fontWeight: 500,
                lineHeight: 1.4,
                cursor: "pointer",
                border: `1px solid ${colors.border.medium}`,
                outline: "none",
                background: "transparent",
                color: colors.text.secondary,
                transition: "all 0.15s ease",
              }}
            >
              修改密码
            </button>
          </div>
        </MobileSectionCard>
      </div>

      {/* ===== 主题 ===== */}
      <div style={{ marginBottom: 12 }}>
        <MobileSectionCard title="主题">
          <SettingRow
            label="当前主题"
            right={
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    fontSize: 13,
                    color: colors.text.secondary,
                    textTransform: "capitalize",
                  }}
                >
                  {mode}
                </span>
                <ToggleSwitch checked={mode === "dark"} onChange={toggle} />
              </div>
            }
          />
        </MobileSectionCard>
      </div>

      {/* ===== 交易配置 ===== */}
      <div style={{ marginBottom: 12 }}>
        <MobileSectionCard title="交易配置">
          <SettingRow
            label="当前模式"
            right={
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  fontSize: 11,
                  fontWeight: 500,
                  lineHeight: 1.3,
                  padding: "2px 10px",
                  borderRadius: 20,
                  backgroundColor: colors.purple[50],
                  color: colors.purple[500],
                }}
              >
                SIMULATION
              </span>
            }
          />
          <div style={{ padding: "10px 14px" }}>
            <button
              onClick={handleModeConfirm}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                padding: "6px 14px",
                borderRadius: `${colors.radius.md}px`,
                fontSize: 13,
                fontWeight: 500,
                lineHeight: 1.4,
                cursor: "pointer",
                border: "none",
                outline: "none",
                background: colors.gradient.primary,
                color: colors.text.inverse,
              }}
            >
              确认模式
            </button>
          </div>
        </MobileSectionCard>
      </div>

      {/* ===== 推送通知 ===== */}
      <div style={{ marginBottom: 12 }}>
        <MobileSectionCard title="推送通知">
          <SettingRow
            label="风控告警"
            right={<ToggleSwitch checked={riskAlertOn} onChange={setRiskAlertOn} />}
          />
          <SettingRow
            label="Agent精选"
            right={
              <ToggleSwitch checked={agentDigestOn} onChange={setAgentDigestOn} />
            }
          />
          <SettingRow
            label="开仓推送"
            right={<ToggleSwitch checked={pushOn} onChange={setPushOn} />}
          />
        </MobileSectionCard>
      </div>

      {/* ===== 关于 ===== */}
      <MobileSectionCard title="关于">
        <SettingRow
          label="版本"
          right={
            <span
              style={{
                fontSize: 13,
                color: colors.text.secondary,
              }}
            >
              1.2.0
            </span>
          }
        />
        <SettingRow
          label="数据源"
          right={
            <span
              style={{
                fontSize: 12,
                color: colors.text.tertiary,
              }}
            >
              AKShare + miniQMT
            </span>
          }
        />
      </MobileSectionCard>
    </div>
  );
}

export default MobileSettings;
