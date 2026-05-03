import { useCallback, useEffect, useState } from "react";
import { App, Modal, Form, Input, Select, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../theme/ThemeContext";
import { useAuthStore } from "../../stores/useAuthStore";
import { authService } from "../../services/authService";
import { settingsService } from "../../services/settingsService";
import type { SettingsMap, LLMProvider } from "../../services/settingsService";

/* ===================================================================
   MobileSettings — 12 大分类 50+ 项参数
   所有配置读写后端 /api/v1/settings/configs，持久化到 PostgreSQL
   =================================================================== */

/* ---- Toggle switch ---- */
const Toggle = ({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) => {
  const { colors } = useTheme();
  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
        onChange(!checked);
      }}
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

/* ---- Setting row ---- */
const Row = ({
  label,
  desc,
  right,
}: {
  label: string;
  desc?: string;
  right: React.ReactNode;
}) => {
  const { colors } = useTheme();
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 14px",
        borderBottom: `1px solid ${colors.border.light}`,
        gap: 12,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13,
            color: colors.text.primary,
            lineHeight: 1.4,
          }}
        >
          {label}
        </div>
        {desc && (
          <div
            style={{
              fontSize: 11,
              color: colors.text.tertiary,
              marginTop: 2,
              lineHeight: 1.3,
            }}
          >
            {desc}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{right}</div>
    </div>
  );
};

/* ---- Number pill badge ---- */
const Badge = ({ label, color }: { label: string; color?: string }) => {
  const { colors } = useTheme();
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: 11,
        fontWeight: 500,
        padding: "2px 10px",
        borderRadius: 20,
        backgroundColor: color ? `${color}18` : colors.purple[50],
        color: color || colors.purple[500],
        lineHeight: 1.3,
      }}
    >
      {label}
    </span>
  );
};

/* ---- Collapse card ---- */
const CollapseCard = ({
  dotColor,
  title,
  defaultOpen = false,
  children,
}: {
  dotColor?: string;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) => {
  const { colors } = useTheme();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      style={{
        background: colors.bg.surface,
        borderRadius: `${colors.radius.md}px`,
        border: `1px solid ${colors.border.light}`,
        overflow: "hidden",
        marginBottom: 10,
      }}
    >
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 14px",
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: dotColor || colors.purple[400],
              flexShrink: 0,
            }}
          />
          <span
            style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}
          >
            {title}
          </span>
        </div>
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke={colors.text.tertiary} strokeWidth="2"
          strokeLinecap="round"
          style={{
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
            flexShrink: 0,
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      {open && <div style={{ paddingBottom: 4 }}>{children}</div>}
    </div>
  );
};

/* ---- Section group label ---- */
const GroupLabel = ({ label }: { label: string }) => {
  const { colors } = useTheme();
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 600,
        color: colors.text.tertiary,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        margin: "16px 0 8px",
        paddingLeft: 2,
      }}
    >
      {label}
    </div>
  );
};

/* ---- LLM 厂商+模型选择器 ---- */
const LLMSelector = ({
  providerKey,
  modelKey,
  configs,
  setConfig,
  colors,
}: {
  providerKey: string;
  modelKey: string;
  configs: SettingsMap;
  setConfig: (key: string, value: string | number | boolean) => void;
  colors: Record<string, any>;
}) => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [providersLoaded, setProvidersLoaded] = useState(false);

  useEffect(() => {
    settingsService.getLLMProviders().then((list) => {
      setProviders(list);
      setProvidersLoaded(true);
    }).catch(() => setProvidersLoaded(true));
  }, []);

  const currentProvider = String(configs[providerKey] ?? "deepseek");
  const currentModel = String(configs[modelKey] ?? "");

  const selectedProvider = providers.find((p) => p.name === currentProvider);
  const availableModels = selectedProvider?.models ?? [];

  const handleProviderChange = (newProvider: string) => {
    setConfig(providerKey, newProvider);
    // 切换厂商时自动设置为该厂商的默认模型
    const provider = providers.find((p) => p.name === newProvider);
    if (provider?.default_model) {
      setConfig(modelKey, provider.default_model);
    }
  };

  const handleCustomModelChange = (value: string) => {
    setConfig(modelKey, value);
  };

  const selectStyle: React.CSSProperties = {
    width: "100%",
    fontSize: 12,
    marginBottom: 6,
  };

  return (
    <div>
      {/* 厂商下拉 */}
      <Select
        showSearch
        style={selectStyle}
        value={currentProvider}
        onChange={handleProviderChange}
        placeholder="选择厂商"
        loading={!providersLoaded}
        options={providers.map((p) => ({
          value: p.name,
          label: p.label,
        }))}
      />

      {/* 模型下拉（预设 + 可自定义输入） */}
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <div style={{ flex: 1 }}>
          <Select
            style={{ width: "100%", fontSize: 12 }}
            value={currentModel || undefined}
            onChange={handleCustomModelChange}
            placeholder="选择或输入模型名"
            showSearch
            allowClear
            options={availableModels.map((m) => ({ value: m, label: m }))}
          />
        </div>
        {selectedProvider && (
          <span style={{ fontSize: 10, color: colors.text.tertiary, whiteSpace: "nowrap" }}>
            {selectedProvider.label}
          </span>
        )}
      </div>
    </div>
  );
};

/* ---- Text input field ---- */
const InputField = ({
  value,
  onChange,
  placeholder,
  type = "text",
  suffix,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  suffix?: string;
}) => {
  const { colors } = useTheme();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 90,
          padding: "6px 8px",
          borderRadius: `${colors.radius.sm}px`,
          border: `1px solid ${colors.border.medium}`,
          background: colors.bg.surface,
          outline: "none",
          color: colors.text.primary,
          fontSize: 12,
          textAlign: type === "number" ? "center" : "left",
          lineHeight: 1.4,
        }}
      />
      {suffix && (
        <span style={{ fontSize: 11, color: colors.text.tertiary, whiteSpace: "nowrap" }}>
          {suffix}
        </span>
      )}
    </div>
  );
};

/* ===================================================================
   Main Component
   =================================================================== */
function MobileSettings() {
  const { message } = App.useApp();
  const { colors, mode, toggle } = useTheme();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [configs, setConfigs] = useState<SettingsMap>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  /* ---- password modal ---- */
  const [pwModalOpen, setPwModalOpen] = useState(false);
  const [pwForm] = Form.useForm();

  /* ---- load configs on mount ---- */
  useEffect(() => {
    settingsService.getConfigs()
      .then(setConfigs)
      .catch(() => message.error("加载配置失败"))
      .finally(() => setLoading(false));
  }, []);

  /* ---- generic setter: saves single key to API ---- */
  const setConfig = useCallback((key: string, value: string | number | boolean) => {
    setConfigs((prev) => ({ ...prev, [key]: value }));
    setSaving(true);
    settingsService.updateConfigs({ [key]: value }).catch(() => {
      message.error(`保存 ${key} 失败`);
      setConfigs((prev) => ({ ...prev, [key]: prev[key] }));
    }).finally(() => setSaving(false));
  }, []);

  /* ---- toggle helper ---- */
  const toggleBool = useCallback((key: string) => {
    const current = configs[key];
    setConfig(key, current === true ? false : true);
  }, [configs, setConfig]);

  /* ---- input change helper ---- */
  const setStr = useCallback((key: string, v: string) => setConfig(key, v), [setConfig]);
  const setNum = useCallback((key: string, v: string) => {
    const n = parseFloat(v);
    setConfig(key, isNaN(n) ? v : n);
  }, [setConfig]);

  /* ---- safe string/number getter ---- */
  const s = (key: string, fallback = ""): string => String(configs[key] ?? fallback);
  const n = (key: string, fallback = 0): string => String(configs[key] ?? fallback);

  /* ---- logout ---- */
  const handleLogout = useCallback(() => {
    useAuthStore.getState().logout();
    navigate("/login");
  }, [navigate]);

  /* ---- change password ---- */
  const handleChangePassword = useCallback(() => setPwModalOpen(true), []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <>
    <div className="page-enter">
      {/* 标题 */}
      <div
        style={{ fontSize: 18, fontWeight: 600, marginBottom: 6, lineHeight: 1.3 }}
      >
        <span style={{
          background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          设置
        </span>
        {saving && <span style={{ fontSize: 11, color: colors.text.tertiary, marginLeft: 8 }}>保存中...</span>}
      </div>
      <div style={{ fontSize: 12, color: colors.text.tertiary, marginBottom: 16 }}>
        系统配置与偏好 · 自动持久化
      </div>

      {/* ==================== 基础 ==================== */}
      <GroupLabel label="基础" />

      {/* 1. 账号安全 */}
      <CollapseCard title="账号安全" dotColor={colors.purple[400]}>
        <Row label="用户名" right={<span style={{ fontSize: 13, color: colors.text.secondary }}>{user?.username || "admin"}</span>} />
        <Row
          label="修改密码"
          desc="修改后将自动登出，需重新登录"
          right={
            <button onClick={(e) => { e.stopPropagation(); handleChangePassword(); }}
              style={{
                padding: "5px 12px", borderRadius: `${colors.radius.sm}px`,
                fontSize: 12, fontWeight: 500, cursor: "pointer",
                border: `1px solid ${colors.border.medium}`,
                background: "transparent", color: colors.text.secondary, lineHeight: 1.4,
              }}
            >修改</button>
          }
        />
        <Row label="自动登出时间" desc="无操作超过此时间自动登出"
          right={<InputField value={n("session_timeout")} onChange={(v) => setNum("session_timeout", v)} suffix="分钟" />}
        />
      </CollapseCard>

      {/* 2. LLM 配置 */}
      <CollapseCard title="LLM 配置" dotColor={colors.purple[400]}>

        {/* ── 每日分析模型 ── */}
        <div style={{ padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}` }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary, marginBottom: 6 }}>每日分析模型</div>
          <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 8 }}>Agent 日常分析使用的模型</div>
          <LLMSelector
            providerKey="daily_analysis_provider"
            modelKey="daily_analysis_model"
            configs={configs}
            setConfig={setConfig}
            colors={colors}
          />
        </div>

        {/* ── 关键决策模型 ── */}
        <div style={{ padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}` }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary, marginBottom: 6 }}>关键决策模型</div>
          <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 8 }}>开仓/止损前的复核模型</div>
          <LLMSelector
            providerKey="key_decision_provider"
            modelKey="key_decision_model"
            configs={configs}
            setConfig={setConfig}
            colors={colors}
          />
        </div>

        {/* ── API Key ── */}
        <Row label="API Key" desc={s("llm_api_key") ? `sk-••••${s("llm_api_key").slice(-4)}` : "未配置"}
          right={<InputField value={s("llm_api_key")} onChange={(v) => setStr("llm_api_key", v)} type="password" placeholder="输入 API Key" />}
        />

        {/* ── 自定义 Base URL（覆盖） ── */}
        <Row label="自定义 Base URL" desc="选填，留空则用厂商默认地址"
          right={<InputField value={s("llm_base_url")} onChange={(v) => setStr("llm_base_url", v)} placeholder="留空=默认" />}
        />

        <Row label="请求超时" right={<InputField value={n("llm_timeout")} onChange={(v) => setNum("llm_timeout", v)} suffix="秒" />} />
        <Row label="最大并发数" right={<InputField value={n("llm_max_concurrent")} onChange={(v) => setNum("llm_max_concurrent", v)} />} />
        <Row label="每月 Token 上限" right={<InputField value={n("llm_monthly_token_limit")} onChange={(v) => setNum("llm_monthly_token_limit", v)} />} />
      </CollapseCard>

      {/* 3. Agent 提示词 */}
      <CollapseCard title="Agent 提示词" dotColor={colors.purple[400]}>
        <Row label="讨论轮数" right={<InputField value={n("agent_discussion_rounds")} onChange={(v) => setNum("agent_discussion_rounds", v)} />} />
        <Row label="输出收敛阈值" right={<InputField value={n("agent_convergence_threshold")} onChange={(v) => setNum("agent_convergence_threshold", v)} />} />
      </CollapseCard>

      {/* ==================== 策略与风控 ==================== */}
      <GroupLabel label="策略与风控" />

      {/* 4. 策略参数 */}
      <CollapseCard title="策略参数" dotColor={colors.semantic.up}>
        <Row label="底部区域阈值" desc="近 N 日跌幅判断" right={<InputField value={n("strategy_bottom_days")} onChange={(v) => setNum("strategy_bottom_days", v)} suffix="日" />} />
        <Row label="跌幅阈值" right={<InputField value={n("strategy_bottom_decline_pct")} onChange={(v) => setNum("strategy_bottom_decline_pct", v)} suffix="%" />} />
        <Row label="暴力下杀跌幅" right={<InputField value={n("strategy_bottom_crash_pct")} onChange={(v) => setNum("strategy_bottom_crash_pct", v)} suffix="%" />} />
        <Row label="板块集中度" desc="主线板块判定标准" right={<InputField value={n("strategy_sector_concentration")} onChange={(v) => setNum("strategy_sector_concentration", v)} suffix="%" />} />
        <Row label="ADX 阈值" right={<InputField value={n("strategy_adx_threshold")} onChange={(v) => setNum("strategy_adx_threshold", v)} />} />
        <Row label="缩量比例" right={<InputField value={n("strategy_shrink_ratio")} onChange={(v) => setNum("strategy_shrink_ratio", v)} suffix="%" />} />
        <Row label="默认止损偏移" right={<InputField value={n("strategy_stop_loss_pct")} onChange={(v) => setNum("strategy_stop_loss_pct", v)} suffix="%" />} />
        <Row label="默认止盈偏移" right={<InputField value={n("strategy_take_profit_pct")} onChange={(v) => setNum("strategy_take_profit_pct", v)} suffix="%" />} />
        <Row label="最大持仓数" right={<InputField value={n("strategy_max_positions")} onChange={(v) => setNum("strategy_max_positions", v)} />} />
      </CollapseCard>

      {/* 5. 风控参数 */}
      <CollapseCard title="风控参数" dotColor={colors.semantic.down}>
        <Row label="单日最大回撤" desc="触发降仓" right={<InputField value={n("risk_daily_max_drawdown")} onChange={(v) => setNum("risk_daily_max_drawdown", v)} suffix="%" />} />
        <Row label="极端回撤阈值" desc="触发清仓" right={<InputField value={n("risk_extreme_drawdown")} onChange={(v) => setNum("risk_extreme_drawdown", v)} suffix="%" />} />
        <Row label="最大连续亏损次数" desc="触发策略暂停" right={<InputField value={n("risk_max_consecutive_losses")} onChange={(v) => setNum("risk_max_consecutive_losses", v)} />} />
        <Row label="单票仓位上限" right={<InputField value={n("risk_single_position_limit")} onChange={(v) => setNum("risk_single_position_limit", v)} suffix="%" />} />
        <Row label="因子拥挤度阈值" right={<InputField value={n("risk_factor_crowding")} onChange={(v) => setNum("risk_factor_crowding", v)} suffix="%" />} />
        <Row label="极端行情阈值" desc="大盘单日跌幅" right={<InputField value={n("risk_extreme_market_decline")} onChange={(v) => setNum("risk_extreme_market_decline", v)} suffix="%" />} />
      </CollapseCard>

      {/* 6. 交易配置 */}
      <CollapseCard title="交易配置" dotColor={colors.semantic.amber}>
        <Row label="当前模式" right={<Badge label={s("trade_mode", "SIMULATION")} />} />
        <Row label="确认模式" desc="manual=手动确认 auto=自动下单"
          right={
            <span style={{ fontSize: 11, color: colors.text.tertiary, cursor: "pointer" }}
              onClick={() => setConfig("trade_confirm_mode", configs["trade_confirm_mode"] === "manual" ? "auto" : "manual")}
            >
              {s("trade_confirm_mode", "manual") === "manual" ? "手动确认" : "自动下单"}
            </span>
          }
        />
        <Row label="佣金费率" right={<InputField value={n("trade_commission_rate")} onChange={(v) => setNum("trade_commission_rate", v)} suffix="万分之" />} />
        <Row label="印花税率" right={<InputField value={n("trade_stamp_tax_rate")} onChange={(v) => setNum("trade_stamp_tax_rate", v)} suffix="千分之" />} />
        <Row label="滑点" right={<InputField value={n("trade_slippage")} onChange={(v) => setNum("trade_slippage", v)} suffix="跳" />} />
      </CollapseCard>

      {/* ==================== 数据与推送 ==================== */}
      <GroupLabel label="数据与推送" />

      {/* 7. 数据源 */}
      <CollapseCard title="数据源" dotColor={colors.semantic.amber}>
        <Row label="AKShare 数据源" desc="免费 A 股行情数据"
          right={<Toggle checked={!!configs["datasource_akshare"]} onChange={() => toggleBool("datasource_akshare")} />}
        />
        <Row label="miniQMT 数据源" desc="实时行情 + 交易通道"
          right={<Toggle checked={!!configs["datasource_qmt"]} onChange={() => toggleBool("datasource_qmt")} />}
        />
        <Row label="miniQMT 地址" right={<InputField value={s("datasource_qmt_host")} onChange={(v) => setStr("datasource_qmt_host", v)} />} />
        <Row label="miniQMT 端口" right={<InputField value={n("datasource_qmt_port")} onChange={(v) => setNum("datasource_qmt_port", v)} />} />
        <Row label="数据同步时间" desc="每日收盘后" right={<InputField value={s("datasource_sync_time")} onChange={(v) => setStr("datasource_sync_time", v)} />} />
        <Row label="舆情轮询间隔" right={<InputField value={n("datasource_news_poll_interval")} onChange={(v) => setNum("datasource_news_poll_interval", v)} suffix="分钟" />} />
      </CollapseCard>

      {/* 8. 新闻配置 */}
      <CollapseCard title="新闻配置" dotColor={colors.semantic.amber}>
        <Row label="华尔街见闻" desc="全球财经快讯"
          right={<Toggle checked={!!configs["news_wsj"]} onChange={() => toggleBool("news_wsj")} />}
        />
        <Row label="AKShare 新闻" desc="东方财富、新浪聚合"
          right={<Toggle checked={!!configs["news_akshare"]} onChange={() => toggleBool("news_akshare")} />}
        />
        <Row label="采集间隔" right={<InputField value={n("news_collect_interval")} onChange={(v) => setNum("news_collect_interval", v)} suffix="分钟" />} />
        <Row label="最多保留" right={<InputField value={n("news_max_retention")} onChange={(v) => setNum("news_max_retention", v)} suffix="条" />} />
        <Row label="热点关键词" right={<InputField value={s("news_hot_keywords")} onChange={(v) => setStr("news_hot_keywords", v)} />} />
      </CollapseCard>

      {/* 9. 推送通知 */}
      <CollapseCard title="推送通知" dotColor={colors.semantic.amber}>
        <Row label="🔔 风控告警" desc="告警类型、当前值、阈值" right={<Toggle checked={!!configs["push_risk_alert"]} onChange={() => toggleBool("push_risk_alert")} />} />
        <Row label="🤖 Agent 精选结果" desc="每日策略运行报告" right={<Toggle checked={!!configs["push_agent_result"]} onChange={() => toggleBool("push_agent_result")} />} />
        <Row label="📈 开仓推送" desc="标的、成交价、仓位" right={<Toggle checked={!!configs["push_open"]} onChange={() => toggleBool("push_open")} />} />
        <Row label="📉 止损/止盈推送" desc="触发原因、盈亏金额" right={<Toggle checked={!!configs["push_stop"]} onChange={() => toggleBool("push_stop")} />} />
        <Row label="📰 舆情推送" desc="事件类型、影响评估" right={<Toggle checked={!!configs["push_news"]} onChange={() => toggleBool("push_news")} />} />
        <Row label="📊 每日复盘推送" desc="操作总结、持仓变化" right={<Toggle checked={!!configs["push_daily_review"]} onChange={() => toggleBool("push_daily_review")} />} />
        <Row label="🔍 开盘前复核推送" desc="外盘波动、计划复核" right={<Toggle checked={!!configs["push_pre_market"]} onChange={() => toggleBool("push_pre_market")} />} />
      </CollapseCard>

      {/* ==================== 高级 ==================== */}
      <GroupLabel label="高级" />

      {/* 10. 复核配置 */}
      <CollapseCard title="复核配置" dotColor={colors.text.tertiary}>
        <Row label="高开取消阈值" desc="超过此比例取消买入计划" right={<InputField value={n("review_high_open_cancel_pct")} onChange={(v) => setNum("review_high_open_cancel_pct", v)} suffix="%" />} />
        <Row label="低开取消阈值" desc="低于此比例取消买入计划" right={<InputField value={n("review_low_open_cancel_pct")} onChange={(v) => setNum("review_low_open_cancel_pct", v)} suffix="%" />} />
        <Row label="外盘波动阈值" desc="触发开盘前复核" right={<InputField value={n("review_overseas_volatility_pct")} onChange={(v) => setNum("review_overseas_volatility_pct", v)} suffix="%" />} />
      </CollapseCard>

      {/* 11. 经验库配置 */}
      <CollapseCard title="经验库配置" dotColor={colors.text.tertiary}>
        <Row label="经验衰减周期" desc="超过此时间权重逐渐降低" right={<InputField value={n("experience_decay_months")} onChange={(v) => setNum("experience_decay_months", v)} suffix="月" />} />
        <Row label="归档周期" desc="未验证的旧经验自动归档" right={<InputField value={n("experience_archive_months")} onChange={(v) => setNum("experience_archive_months", v)} suffix="月" />} />
        <Row label="市场状态权重" right={<InputField value={n("experience_weight_market")} onChange={(v) => setNum("experience_weight_market", v)} suffix="%" />} />
        <Row label="板块属性权重" right={<InputField value={n("experience_weight_sector")} onChange={(v) => setNum("experience_weight_sector", v)} suffix="%" />} />
        <Row label="技术形态权重" right={<InputField value={n("experience_weight_tech")} onChange={(v) => setNum("experience_weight_tech", v)} suffix="%" />} />
        <Row label="资金特征权重" right={<InputField value={n("experience_weight_fund")} onChange={(v) => setNum("experience_weight_fund", v)} suffix="%" />} />
      </CollapseCard>

      {/* 12. 系统配置 */}
      <CollapseCard title="系统配置" dotColor={colors.text.tertiary}>
        <Row label="日志级别" right={<Badge label={s("log_level", "INFO")} />} />
        <Row label="全局限流" right={<span style={{ fontSize: 12, color: colors.text.secondary }}>{n("rate_limit")} 次/秒/IP</span>} />
        <Row label="备份时间" right={<InputField value={s("backup_time")} onChange={(v) => setStr("backup_time", v)} />} />
        <Row label="备份保留" right={<InputField value={n("backup_retention_days")} onChange={(v) => setNum("backup_retention_days", v)} suffix="天" />} />
        <Row label="粒子效果" desc="背景粒子动画"
          right={<Toggle checked={!!configs["particle_effect"]} onChange={() => toggleBool("particle_effect")} />}
        />
        <Row
          label="主题"
          right={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, color: colors.text.secondary, textTransform: "capitalize" }}>
                {mode === "dark" ? "暗黑紫色" : "暖白柔光"}
              </span>
              <Toggle checked={mode === "dark"} onChange={toggle} />
            </div>
          }
        />
      </CollapseCard>

      {/* ==================== 底部 ==================== */}
      <div style={{ marginTop: 20, marginBottom: 24 }}>
        <div style={{
          background: colors.bg.surface, borderRadius: `${colors.radius.md}px`,
          border: `1px solid ${colors.border.light}`, overflow: "hidden",
        }}>
          <Row label="版本" right={<span style={{ fontSize: 13, color: colors.text.secondary }}>1.2.0</span>} />
          <Row label="数据源" right={<span style={{ fontSize: 12, color: colors.text.tertiary }}>AKShare + miniQMT</span>} />
          <div style={{ padding: "10px 14px" }}>
            <button onClick={(e) => { e.stopPropagation(); handleLogout(); }}
              style={{
                width: "100%", padding: "10px 14px", borderRadius: `${colors.radius.md}px`,
                fontSize: 14, fontWeight: 500, cursor: "pointer", border: "none", outline: "none",
                background: colors.semantic.upBg, color: colors.semantic.up, lineHeight: 1.4,
              }}
            >退出登录</button>
          </div>
        </div>
      </div>
    </div>

      {/* 修改密码 Modal */}
      <Modal title="修改密码" open={pwModalOpen}
        onCancel={() => { setPwModalOpen(false); pwForm.resetFields(); }}
        onOk={async () => {
          try {
            const values = await pwForm.validateFields();
            if (values.newPassword !== values.confirmPassword) {
              message.error("两次输入的新密码不一致"); return;
            }
            await authService.changePassword(values.oldPassword, values.newPassword);
            message.success("密码修改成功，请重新登录");
            setPwModalOpen(false); pwForm.resetFields();
            useAuthStore.getState().logout();
            navigate("/login");
          } catch (err: any) {
            if (err?.errorFields) return;
            message.error("密码修改失败：" + (err?.response?.data?.detail || err?.message || "未知错误"));
          }
        }}
        okText="确认修改" cancelText="取消"
      >
        <Form form={pwForm} layout="vertical">
          <Form.Item name="oldPassword" label="当前密码" rules={[{ required: true, message: "请输入当前密码" }]}>
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item name="newPassword" label="新密码" rules={[{ required: true, message: "请输入新密码" }, { min: 6, message: "密码至少6位" }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item name="confirmPassword" label="确认新密码"
            rules={[
              { required: true, message: "请再次输入新密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("newPassword") === value) return Promise.resolve();
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password placeholder="再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
  </>
  );
}

export default MobileSettings;
