import { useCallback, useEffect, useState } from "react";
import { App, Modal, Form, Input, Select, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../theme/ThemeContext";
import { useAuthStore } from "../../stores/useAuthStore";
import { authService } from "../../services/authService";
import { settingsService } from "../../services/settingsService";
import type { SettingsMap, LLMProvider, LLMConnection, TradeModeInfo } from "../../services/settingsService";

/* ─── 子组件 ─── */
import Row from "./settings/Row";
import Toggle from "./settings/Toggle";
import Badge from "./settings/Badge";
import InputField from "./settings/InputField";
import CollapseCard from "./settings/CollapseCard";
import GroupLabel from "./settings/GroupLabel";
import ConnectionCard from "./settings/ConnectionCard";
import UsageSlot from "./settings/UsageSlot";

/* ===================================================================
   MobileSettings — 新版：6 卡心智分组 + InfoTip 内联说明
   =================================================================== */

/** 检查配置项是否已被用户修改（非空且不是默认值状态） */
function isConfigured(configs: SettingsMap, key: string): boolean {
  const v = configs[key];
  return v !== undefined && v !== null && v !== "";
}

export default function MobileSettings() {
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

  /* ---- LLM 连接 + 厂商预设 ---- */
  const [llmConnections, setLlmConnections] = useState<LLMConnection[]>([]);
  const [allProviders, setAllProviders] = useState<LLMProvider[]>([]);
  const [llmConnectionsLoading, setLlmConnectionsLoading] = useState(true);

  /* ---- 交易模式 ---- */
  const [tradeMode, setTradeMode] = useState<TradeModeInfo>({
    current_mode: "SIMULATION",
    confirm_mode: "advisory",
    emergency_stop: false,
  });

  /* ---- load configs on mount ---- */
  useEffect(() => {
    settingsService.getConfigs()
      .then(setConfigs)
      .catch(() => message.error("加载配置失败"))
      .finally(() => setLoading(false));
  }, []);

  /* ---- load LLM providers + connections on mount ---- */
  const loadLLMConnections = useCallback(() => {
    Promise.all([
      settingsService.getLLMProviders(),
      settingsService.getLLMConnections(),
    ]).then(([providers, conns]) => {
      setAllProviders(providers);
      setLlmConnections(conns);
    }).catch(() => {}).finally(() => setLlmConnectionsLoading(false));
  }, []);
  useEffect(() => { loadLLMConnections(); }, []);

  /* ---- load TradeMode ---- */
  useEffect(() => {
    settingsService.getTradeMode().then(setTradeMode).catch(() => {});
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
    setConfig(key, configs[key] === true ? false : true);
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
      <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6, lineHeight: 1.3 }}>
        <span style={{
          background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          设置
        </span>
        {saving && <span style={{ fontSize: 11, color: colors.text.tertiary, marginLeft: 8 }}>保存中...</span>}
      </div>
      <div style={{ fontSize: 12, color: colors.text.tertiary, marginBottom: 16 }}>
        系统配置与偏好 · 自动持久化
      </div>

      {/* ==================== ① 我的账户 ==================== */}
      <CollapseCard title="我的账户" subtitle="登录信息、安全设置"
        dotColor={colors.purple[400]}
        totalItems={1} configuredItems={[isConfigured(configs, "session_timeout")].filter(Boolean).length}>
        <Row label="用户名" right={<span style={{ fontSize: 13, color: colors.text.secondary }}>{user?.username || "admin"}</span>} />
        <Row label="修改密码" desc="修改后将自动登出，需重新登录"
          right={
            <button onClick={(e) => { e.stopPropagation(); handleChangePassword(); }}
              style={{ padding: "5px 12px", borderRadius: `${colors.radius.sm}px`, fontSize: 12,
                fontWeight: 500, cursor: "pointer", border: `1px solid ${colors.border.medium}`,
                background: "transparent", color: colors.text.secondary, lineHeight: 1.4 }}>
              修改</button>
          } />
        <Row label="自动登出时间" desc="无操作超过此时间自动登出" configKey="session_timeout"
          right={<InputField value={n("session_timeout")} onChange={(v) => setNum("session_timeout", v)} suffix="分钟" />} />
      </CollapseCard>

      {/* ==================== ② AI 模型 ==================== */}
      <CollapseCard title="AI 模型" subtitle="厂商 API 连接 + 任务模型分配"
        dotColor={colors.purple[400]}
        totalItems={5} configuredItems={[
          isConfigured(configs, "llm_timeout"),
          isConfigured(configs, "llm_max_concurrent"),
          isConfigured(configs, "llm_monthly_token_limit"),
          isConfigured(configs, "agent_discussion_rounds"),
          isConfigured(configs, "agent_convergence_threshold"),
        ].filter(Boolean).length}>

        {/* 我的 API 连接 */}
        <div style={{ padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}` }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: colors.text.primary, marginBottom: 2 }}>🔌 我的 API 连接</div>
          <div style={{ fontSize: 10, color: colors.text.tertiary, marginBottom: 8 }}>
            每个厂商配一次 Key 和 URL，后续所有模型使用分配都用这些连接
          </div>
          {(llmConnectionsLoading || allProviders.length === 0) ? (
            <span style={{ fontSize: 11, color: colors.text.tertiary }}>加载中...</span>
          ) : (
            allProviders.map((p) => {
              const conn = llmConnections.find((c) => c.provider_name === p.name);
              return (
                <ConnectionCard key={p.name} provider={p} connection={conn}
                  onSave={(providerName, apiKey, baseUrl) => {
                    settingsService.upsertLLMConnection(providerName, apiKey, baseUrl).then(() => {
                      message.success(`${p.label} 连接已保存`);
                      loadLLMConnections();
                    }).catch((e) => message.error("保存失败: " + (e?.response?.data?.detail || e.message)));
                  }}
                  onDelete={(providerName) => {
                    Modal.confirm({
                      title: `删除 ${p.label} 的连接？`,
                      content: "API Key 将从系统中移除",
                      onOk: () => settingsService.deleteLLMConnection(providerName).then(() => {
                        message.success("已删除");
                        loadLLMConnections();
                      }),
                    });
                  }}
                  colors={colors} />
              );
            })
          )}
          <div style={{ padding: "8px 10px" }}>
            <span style={{ fontSize: 10, color: colors.text.tertiary }}>
              厂商列表中附带模型预设供选择，如需其他厂商请修改预设
            </span>
          </div>
        </div>

        {/* 模型使用分配 */}
        <GroupLabel label="模型使用分配" />
        <div style={{ fontSize: 10, color: colors.text.tertiary, padding: "0 14px 8px" }}>
          每个任务指定用什么厂商的什么模型。未配 Key 的厂商不可选。
        </div>

        <UsageSlot title="每日分析" desc="Agent 日常分析使用的模型"
          providerKey="daily_analysis_provider" modelKey="daily_analysis_model"
          connections={llmConnections.map((c) => c.provider_name)}
          allProviders={allProviders} configs={configs} setConfig={setConfig} colors={colors} />

        <UsageSlot title="关键决策" desc="开仓/止损前的复核模型"
          providerKey="key_decision_provider" modelKey="key_decision_model"
          reuseKey="daily_analysis"
          connections={llmConnections.map((c) => c.provider_name)}
          allProviders={allProviders} configs={configs} setConfig={setConfig} colors={colors} />

        <Row label="请求超时" configKey="llm_timeout"
          right={<InputField value={n("llm_timeout")} onChange={(v) => setNum("llm_timeout", v)} suffix="秒" />} />
        <Row label="最大并发数" configKey="llm_max_concurrent"
          right={<InputField value={n("llm_max_concurrent")} onChange={(v) => setNum("llm_max_concurrent", v)} />} />
        <Row label="每月 Token 上限" configKey="llm_monthly_token_limit"
          right={<InputField value={n("llm_monthly_token_limit")} onChange={(v) => setNum("llm_monthly_token_limit", v)} />} />
      </CollapseCard>

      {/* ==================== ③ 交易策略 ==================== */}
      <CollapseCard title="交易策略" subtitle="选股参数、止盈止损、仓位控制"
        dotColor={colors.semantic.up}
        totalItems={14} configuredItems={[
          "strategy_bottom_days","strategy_bottom_decline_pct","strategy_bottom_crash_pct",
          "strategy_bottom_min_klines","strategy_sector_concentration","strategy_sector_check_days",
          "strategy_adx_threshold","strategy_shrink_ratio","strategy_momentum_drop_pct",
          "strategy_momentum_min_amount","strategy_momentum_min_klines",
          "strategy_stop_loss_pct","strategy_take_profit_pct","strategy_max_positions",
        ].map((k) => isConfigured(configs, k)).filter(Boolean).length}>

        <GroupLabel label="底部量能异动（S1）" />
        <Row label="底部区域天数" configKey="strategy_bottom_days"
          right={<InputField value={n("strategy_bottom_days")} onChange={(v) => setNum("strategy_bottom_days", v)} suffix="日" />} />
        <Row label="跌幅阈值" configKey="strategy_bottom_decline_pct"
          right={<InputField value={n("strategy_bottom_decline_pct")} onChange={(v) => setNum("strategy_bottom_decline_pct", v)} suffix="%" />} />
        <Row label="暴力下杀跌幅" configKey="strategy_bottom_crash_pct"
          right={<InputField value={n("strategy_bottom_crash_pct")} onChange={(v) => setNum("strategy_bottom_crash_pct", v)} suffix="%" />} />
        <Row label="最少 K 线数" configKey="strategy_bottom_min_klines"
          right={<InputField value={n("strategy_bottom_min_klines")} onChange={(v) => setNum("strategy_bottom_min_klines", v)} suffix="根" />} />

        <GroupLabel label="趋势动量低吸（S2）" />
        <Row label="回踩跌幅" configKey="strategy_momentum_drop_pct"
          right={<InputField value={n("strategy_momentum_drop_pct")} onChange={(v) => setNum("strategy_momentum_drop_pct", v)} suffix="%" />} />
        <Row label="最低成交额" configKey="strategy_momentum_min_amount"
          right={<InputField value={n("strategy_momentum_min_amount")} onChange={(v) => setNum("strategy_momentum_min_amount", v)} suffix="元" />} />
        <Row label="最少 K 线数" configKey="strategy_momentum_min_klines"
          right={<InputField value={n("strategy_momentum_min_klines")} onChange={(v) => setNum("strategy_momentum_min_klines", v)} suffix="根" />} />
        <Row label="ADX 阈值" configKey="strategy_adx_threshold"
          right={<InputField value={n("strategy_adx_threshold")} onChange={(v) => setNum("strategy_adx_threshold", v)} />} />
        <Row label="缩量比例" configKey="strategy_shrink_ratio"
          right={<InputField value={n("strategy_shrink_ratio")} onChange={(v) => setNum("strategy_shrink_ratio", v)} suffix="%" />} />

        <GroupLabel label="板块筛选" />
        <Row label="板块集中度" configKey="strategy_sector_concentration"
          right={<InputField value={n("strategy_sector_concentration")} onChange={(v) => setNum("strategy_sector_concentration", v)} suffix="%" />} />
        <Row label="板块持续性" configKey="strategy_sector_check_days"
          right={<InputField value={n("strategy_sector_check_days")} onChange={(v) => setNum("strategy_sector_check_days", v)} suffix="天" />} />

        <GroupLabel label="止盈止损" />
        <Row label="默认止损" configKey="strategy_stop_loss_pct"
          right={<InputField value={n("strategy_stop_loss_pct")} onChange={(v) => setNum("strategy_stop_loss_pct", v)} suffix="%" />} />
        <Row label="默认止盈" configKey="strategy_take_profit_pct"
          right={<InputField value={n("strategy_take_profit_pct")} onChange={(v) => setNum("strategy_take_profit_pct", v)} suffix="%" />} />
        <Row label="最大持仓数" configKey="strategy_max_positions"
          right={<InputField value={n("strategy_max_positions")} onChange={(v) => setNum("strategy_max_positions", v)} />} />
      </CollapseCard>

      {/* ==================== ④ 风控与执行 ==================== */}
      <CollapseCard title="风控与执行" subtitle="回撤保护、仓位限制、交易成本"
        dotColor={colors.semantic.down}
        totalItems={10} configuredItems={[
          "risk_daily_max_drawdown","risk_extreme_drawdown","risk_max_consecutive_losses",
          "risk_single_position_limit","risk_factor_crowding","risk_extreme_market_decline",
          "trade_commission_rate","trade_stamp_tax_rate","trade_slippage",
        ].map((k) => isConfigured(configs, k)).filter(Boolean).length}>

        <GroupLabel label="交易模式" />
        <div style={{ padding: "10px 14px", borderBottom: `1px solid ${colors.border.light}` }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: colors.text.primary, marginBottom: 2 }}>交易模式</div>
          <div style={{ fontSize: 10, color: colors.text.tertiary, marginBottom: 6 }}>
            SIMULATION=模拟 / PAPER=模拟真金 / LIVE=实盘
          </div>
          <Select style={{ width: "100%", fontSize: 12 }}
            value={tradeMode.current_mode}
            onChange={(value: string) => {
              settingsService.updateTradeMode(value).then(() => {
                message.success(`交易模式已切换为 ${value}`);
                setTradeMode((prev: any) => ({ ...prev, current_mode: value }));
              }).catch((e: any) => message.error("切换失败: " + (e?.response?.data?.detail || e.message)));
            }}
            options={[
              { value: "SIMULATION", label: "🟢 模拟（SIMULATION）" },
              { value: "PAPER", label: "🟡 模拟真金（PAPER）" },
              { value: "LIVE", label: "🔴 实盘（LIVE）" },
            ]} />
        </div>
        <Row label="确认模式" desc="advisory=建议  semi_auto=半自动  full_auto=全自动"
          right={
            <span style={{ fontSize: 11, color: colors.text.tertiary, cursor: "pointer" }}
              onClick={() => {
                const modes = ["advisory", "semi_auto", "full_auto"];
                const idx = modes.indexOf(tradeMode.confirm_mode);
                const next = modes[(idx + 1) % modes.length];
                settingsService.updateTradeMode(undefined, next).then(() => {
                  message.success(`确认模式已切换为 ${next}`);
                  setTradeMode((prev: any) => ({ ...prev, confirm_mode: next }));
                }).catch((_: any) => message.error("切换失败"));
              }}>
              {tradeMode.confirm_mode === "advisory" ? "💡 顾问建议" :
               tradeMode.confirm_mode === "semi_auto" ? "⚡ 半自动" : "🤖 全自动"}
            </span>
          } />

        <GroupLabel label="风控参数" />
        <Row label="单日最大回撤" desc="触发降半仓" configKey="risk_daily_max_drawdown"
          right={<InputField value={n("risk_daily_max_drawdown")} onChange={(v) => setNum("risk_daily_max_drawdown", v)} suffix="%" />} />
        <Row label="极端回撤阈值" desc="触发清仓" configKey="risk_extreme_drawdown"
          right={<InputField value={n("risk_extreme_drawdown")} onChange={(v) => setNum("risk_extreme_drawdown", v)} suffix="%" />} />
        <Row label="最大连续亏损" desc="触发策略暂停" configKey="risk_max_consecutive_losses"
          right={<InputField value={n("risk_max_consecutive_losses")} onChange={(v) => setNum("risk_max_consecutive_losses", v)} suffix="次" />} />
        <Row label="单票仓位上限" configKey="risk_single_position_limit"
          right={<InputField value={n("risk_single_position_limit")} onChange={(v) => setNum("risk_single_position_limit", v)} suffix="%" />} />
        <Row label="因子拥挤度阈值" configKey="risk_factor_crowding"
          right={<InputField value={n("risk_factor_crowding")} onChange={(v) => setNum("risk_factor_crowding", v)} suffix="%" />} />
        <Row label="极端行情阈值" desc="大盘单日跌幅" configKey="risk_extreme_market_decline"
          right={<InputField value={n("risk_extreme_market_decline")} onChange={(v) => setNum("risk_extreme_market_decline", v)} suffix="%" />} />

        <GroupLabel label="交易成本" />
        <Row label="佣金费率" configKey="trade_commission_rate"
          right={<InputField value={n("trade_commission_rate")} onChange={(v) => setNum("trade_commission_rate", v)} suffix="万分之" />} />
        <Row label="印花税率" configKey="trade_stamp_tax_rate"
          right={<InputField value={n("trade_stamp_tax_rate")} onChange={(v) => setNum("trade_stamp_tax_rate", v)} suffix="千分之" />} />
        <Row label="滑点" configKey="trade_slippage"
          right={<InputField value={n("trade_slippage")} onChange={(v) => setNum("trade_slippage", v)} suffix="跳" />} />
      </CollapseCard>

      {/* ==================== ⑤ 数据与通知 ==================== */}
      <CollapseCard title="数据与通知" subtitle="数据源、新闻、推送开关"
        dotColor={colors.semantic.amber}
        totalItems={14} configuredItems={[
          "datasource_akshare","datasource_qmt",
          "datasource_qmt_host","datasource_qmt_port",
          "datasource_sync_time","datasource_news_poll_interval",
          "news_wsj","news_akshare","news_collect_interval","news_max_retention","news_hot_keywords",
          "push_risk_alert","push_agent_result","push_open","push_stop","push_news","push_daily_review","push_pre_market",
        ].map((k) => isConfigured(configs, k)).filter(Boolean).length}>

        <GroupLabel label="数据源" />
        <Row label="AKShare 数据源" desc="免费 A 股行情数据"
          right={<Toggle checked={!!configs["datasource_akshare"]} onChange={() => toggleBool("datasource_akshare")} />} />
        <Row label="miniQMT 数据源" desc="实时行情 + 交易通道"
          right={<Toggle checked={!!configs["datasource_qmt"]} onChange={() => toggleBool("datasource_qmt")} />} />
        <Row label="miniQMT 地址" configKey="datasource_qmt_host"
          right={<InputField value={s("datasource_qmt_host")} onChange={(v) => setStr("datasource_qmt_host", v)} />} />
        <Row label="miniQMT 端口" configKey="datasource_qmt_port"
          right={<InputField value={n("datasource_qmt_port")} onChange={(v) => setNum("datasource_qmt_port", v)} />} />
        <Row label="数据同步时间" desc="每日收盘后" configKey="datasource_sync_time"
          right={<InputField value={s("datasource_sync_time")} onChange={(v) => setStr("datasource_sync_time", v)} />} />
        <Row label="舆情轮询间隔" configKey="datasource_news_poll_interval"
          right={<InputField value={n("datasource_news_poll_interval")} onChange={(v) => setNum("datasource_news_poll_interval", v)} suffix="分钟" />} />

        <GroupLabel label="新闻" />
        <Row label="华尔街见闻" desc="全球财经快讯"
          right={<Toggle checked={!!configs["news_wsj"]} onChange={() => toggleBool("news_wsj")} />} />
        <Row label="AKShare 新闻" desc="东方财富、新浪聚合"
          right={<Toggle checked={!!configs["news_akshare"]} onChange={() => toggleBool("news_akshare")} />} />
        <Row label="采集间隔" configKey="news_collect_interval"
          right={<InputField value={n("news_collect_interval")} onChange={(v) => setNum("news_collect_interval", v)} suffix="分钟" />} />
        <Row label="最多保留" configKey="news_max_retention"
          right={<InputField value={n("news_max_retention")} onChange={(v) => setNum("news_max_retention", v)} suffix="条" />} />
        <Row label="热点关键词" configKey="news_hot_keywords"
          right={<InputField value={s("news_hot_keywords")} onChange={(v) => setStr("news_hot_keywords", v)} />} />

        <GroupLabel label="推送通知" />
        <Row label="🔔 风控告警" configKey="push_risk_alert"
          right={<Toggle checked={!!configs["push_risk_alert"]} onChange={() => toggleBool("push_risk_alert")} />} />
        <Row label="🤖 Agent 精选结果" configKey="push_agent_result"
          right={<Toggle checked={!!configs["push_agent_result"]} onChange={() => toggleBool("push_agent_result")} />} />
        <Row label="📈 开仓推送" configKey="push_open"
          right={<Toggle checked={!!configs["push_open"]} onChange={() => toggleBool("push_open")} />} />
        <Row label="📉 止损/止盈推送" configKey="push_stop"
          right={<Toggle checked={!!configs["push_stop"]} onChange={() => toggleBool("push_stop")} />} />
        <Row label="📰 舆情推送" configKey="push_news"
          right={<Toggle checked={!!configs["push_news"]} onChange={() => toggleBool("push_news")} />} />
        <Row label="📊 每日复盘推送" configKey="push_daily_review"
          right={<Toggle checked={!!configs["push_daily_review"]} onChange={() => toggleBool("push_daily_review")} />} />
        <Row label="🔍 开盘前复核推送" configKey="push_pre_market"
          right={<Toggle checked={!!configs["push_pre_market"]} onChange={() => toggleBool("push_pre_market")} />} />
      </CollapseCard>

      {/* ==================== ⑥ 系统 ==================== */}
      <CollapseCard title="系统" subtitle="复核、经验库、日志、备份、主题"
        dotColor={colors.text.tertiary}
        totalItems={14} configuredItems={[
          "review_high_open_cancel_pct","review_low_open_cancel_pct","review_overseas_volatility_pct",
          "experience_decay_months","experience_archive_months",
          "experience_weight_market","experience_weight_sector","experience_weight_tech","experience_weight_fund",
          "log_level","rate_limit","backup_time","backup_retention_days","particle_effect",
        ].map((k) => isConfigured(configs, k)).filter(Boolean).length}>

        <GroupLabel label="开盘复核" />
        <Row label="高开取消阈值" configKey="review_high_open_cancel_pct"
          right={<InputField value={n("review_high_open_cancel_pct")} onChange={(v) => setNum("review_high_open_cancel_pct", v)} suffix="%" />} />
        <Row label="低开取消阈值" configKey="review_low_open_cancel_pct"
          right={<InputField value={n("review_low_open_cancel_pct")} onChange={(v) => setNum("review_low_open_cancel_pct", v)} suffix="%" />} />
        <Row label="外盘波动阈值" configKey="review_overseas_volatility_pct"
          right={<InputField value={n("review_overseas_volatility_pct")} onChange={(v) => setNum("review_overseas_volatility_pct", v)} suffix="%" />} />

        <GroupLabel label="经验库" />
        <Row label="衰减周期" configKey="experience_decay_months"
          right={<InputField value={n("experience_decay_months")} onChange={(v) => setNum("experience_decay_months", v)} suffix="月" />} />
        <Row label="归档周期" configKey="experience_archive_months"
          right={<InputField value={n("experience_archive_months")} onChange={(v) => setNum("experience_archive_months", v)} suffix="月" />} />
        <Row label="市场状态权重" configKey="experience_weight_market"
          right={<InputField value={n("experience_weight_market")} onChange={(v) => setNum("experience_weight_market", v)} suffix="%" />} />
        <Row label="板块属性权重" configKey="experience_weight_sector"
          right={<InputField value={n("experience_weight_sector")} onChange={(v) => setNum("experience_weight_sector", v)} suffix="%" />} />
        <Row label="技术形态权重" configKey="experience_weight_tech"
          right={<InputField value={n("experience_weight_tech")} onChange={(v) => setNum("experience_weight_tech", v)} suffix="%" />} />
        <Row label="资金特征权重" configKey="experience_weight_fund"
          right={<InputField value={n("experience_weight_fund")} onChange={(v) => setNum("experience_weight_fund", v)} suffix="%" />} />

        <GroupLabel label="系统配置" />
        <Row label="日志级别" configKey="log_level"
          right={<Badge label={s("log_level", "INFO")} />} />
        <Row label="全局限流" configKey="rate_limit"
          right={<span style={{ fontSize: 12, color: colors.text.secondary }}>{n("rate_limit")} 次/秒/IP</span>} />
        <Row label="备份时间" configKey="backup_time"
          right={<InputField value={s("backup_time")} onChange={(v) => setStr("backup_time", v)} />} />
        <Row label="备份保留" configKey="backup_retention_days"
          right={<InputField value={n("backup_retention_days")} onChange={(v) => setNum("backup_retention_days", v)} suffix="天" />} />
        <Row label="粒子效果" desc="背景粒子动画" configKey="particle_effect"
          right={<Toggle checked={!!configs["particle_effect"]} onChange={() => toggleBool("particle_effect")} />} />
        <Row label="主题"
          right={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, color: colors.text.secondary, textTransform: "capitalize" }}>
                {mode === "dark" ? "暗黑紫色" : "暖白柔光"}
              </span>
              <Toggle checked={mode === "dark"} onChange={toggle} />
            </div>
          } />
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
              style={{ width: "100%", padding: "10px 14px", borderRadius: `${colors.radius.md}px`,
                fontSize: 14, fontWeight: 500, cursor: "pointer", border: "none", outline: "none",
                background: colors.semantic.upBg, color: colors.semantic.up, lineHeight: 1.4 }}>
              退出登录</button>
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
        okText="确认修改" cancelText="取消">
        <Form form={pwForm} layout="vertical">
          <Form.Item name="oldPassword" label="当前密码" rules={[{ required: true, message: "请输入当前密码" }]}>
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item name="newPassword" label="新密码" rules={[{ required: true, message: "请输入新密码" }, { min: 6, message: "密码至少6位" }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item name="confirmPassword" label="确认新密码" rules={[
            { required: true, message: "请再次输入新密码" },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue("newPassword") === value) return Promise.resolve();
                return Promise.reject(new Error("两次输入的密码不一致"));
              },
            }),
          ]}>
            <Input.Password placeholder="再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
  </>
  );
}
