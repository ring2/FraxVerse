import { useCallback, useState } from "react";
import { App, Modal, Form, Input } from "antd";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../theme/ThemeContext";
import { useAuthStore } from "../../stores/useAuthStore";
import { authService } from "../../services/authService";

/* ===================================================================
   MobileSettings — 12 大分类 50+ 项参数
   对齐设计稿 FraxVerse-V2-AllPages.html 行 722~1259
   移动端使用折叠卡片 + SettingRow 列表，保留所有核心交互
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

/* ---- Text input field (mobile friendly) ---- */
const InputField = ({
  placeholder,
  defaultValue,
  type = "text",
  suffix,
}: {
  placeholder?: string;
  defaultValue?: string;
  type?: string;
  suffix?: string;
}) => {
  const { colors } = useTheme();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <input
        type={type}
        defaultValue={defaultValue}
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

/* ===================================================================
   折叠卡片容器 —— 左侧 dot + 标题，可展开/收起
   =================================================================== */
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
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: colors.text.primary,
            }}
          >
            {title}
          </span>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke={colors.text.tertiary}
          strokeWidth="2"
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

/* ===================================================================
   Section Group — "12 大分类" 的分组标题
   =================================================================== */
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

/* ===================================================================
   Main Component
   =================================================================== */
function MobileSettings() {
  const { message } = App.useApp();
  const { colors, mode, toggle } = useTheme();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  /* ---- password modal state ---- */
  const [pwModalOpen, setPwModalOpen] = useState(false);
  const [pwForm] = Form.useForm();

  /* ---- push notification state ---- */
  const [pushStates, setPushStates] = useState({
    risk: true,
    agentResult: true,
    open: true,
    stop: true,
    news: true,
    dailyReview: true,
    preMarket: true,
  });
  const togglePush = (k: keyof typeof pushStates) =>
    setPushStates((s) => ({ ...s, [k]: !s[k] }));

  /* ---- data source state ---- */
  const [dsStates, setDsStates] = useState({ akshare: true, qmt: true, newsWsj: true, newsAk: false, newsSina: false });
  const toggleDs = (k: keyof typeof dsStates) => setDsStates((s) => ({ ...s, [k]: !s[k] }));

  const handleLogout = useCallback(() => {
    useAuthStore.getState().logout();
    navigate("/login");
  }, [navigate]);

  const handleChangePassword = useCallback(() => {
    setPwModalOpen(true);
  }, []);

  return (
    <>
    <div className="page-enter">
      {/* 标题 */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          marginBottom: 6,
          lineHeight: 1.3,
        }}
      >
        <span style={{
          background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          设置
        </span>
      </div>
      <div
        style={{
          fontSize: 12,
          color: colors.text.tertiary,
          marginBottom: 16,
        }}
      >
        系统配置与偏好 · 12 大分类 50+ 项参数
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
            <button
              onClick={(e) => { e.stopPropagation(); handleChangePassword(); }}
              style={{
                padding: "5px 12px",
                borderRadius: `${colors.radius.sm}px`,
                fontSize: 12,
                fontWeight: 500,
                cursor: "pointer",
                border: `1px solid ${colors.border.medium}`,
                background: "transparent",
                color: colors.text.secondary,
                lineHeight: 1.4,
                transition: "all 0.15s ease",
              }}
            >
              修改
            </button>
          }
        />
        <Row label="自动登出时间" desc="无操作超过此时间自动登出" right={<InputField type="number" defaultValue="60" suffix="分钟" />} />
        <Row
          label="登录日志"
          desc="最近 20 条登录记录"
          right={
            <span style={{ fontSize: 11, color: colors.text.tertiary }}>查看 →</span>
          }
        />
      </CollapseCard>

      {/* 2. LLM 配置 */}
      <CollapseCard title="LLM 配置" dotColor={colors.purple[400]}>
        <Row
          label="每日分析模型"
          desc="Agent 日常分析使用的模型"
          right={<Badge label="DeepSeek V3" />}
        />
        <Row
          label="关键决策模型"
          desc="开仓/止损前的复核模型"
          right={<Badge label="Claude Sonnet" color={colors.purple[500]} />}
        />
        <Row
          label="DeepSeek API Key"
          desc="sk-••••••••••••••••••••••••"
          right={
            <span style={{ fontSize: 11, color: colors.text.tertiary }}>修改</span>
          }
        />
        <Row label="请求超时" right={<InputField type="number" defaultValue="60" suffix="秒" />} />
        <Row label="最大并发数" right={<InputField type="number" defaultValue="8" />} />
        <Row label="每月 Token 上限" right={<InputField type="number" defaultValue="10000000" />} />
      </CollapseCard>

      {/* 3. Agent 提示词 */}
      <CollapseCard title="Agent 提示词" dotColor={colors.purple[400]}>
        {(["主线猎手", "资金侦探", "情绪捕手", "经验法官"] as const).map((name, i) => (
          <Row
            key={name}
            label={name}
            desc={["擅长宏观政策与主线猎捕", "追踪主力资金建仓出货", "识别情绪拐点", "综合评判与修正"][i]}
            right={
              <span style={{ fontSize: 11, color: colors.text.tertiary }}>编辑</span>
            }
          />
        ))}
        <Row label="讨论轮数" right={<InputField type="number" defaultValue="2" />} />
        <Row label="输出收敛阈值" right={<InputField type="number" defaultValue="0.70" />} />
      </CollapseCard>

      {/* ==================== 策略与风控 ==================== */}
      <GroupLabel label="策略与风控" />

      {/* 4. 策略参数 */}
      <CollapseCard title="策略参数" dotColor={colors.semantic.up}>
        <Row label="周期底部·底部区域阈值" desc="近 N 日跌幅判断" right={<InputField type="number" defaultValue="60" suffix="日" />} />
        <Row label="周期底部·跌幅阈值" right={<InputField type="number" defaultValue="20" suffix="%" />} />
        <Row label="周期底部·暴力下杀跌幅" right={<InputField type="number" defaultValue="5" suffix="%" />} />
        <Row label="趋势动量·板块集中度" desc="主线板块判定标准" right={<InputField type="number" defaultValue="12" suffix="%" />} />
        <Row label="趋势动量·ADX 阈值" right={<InputField type="number" defaultValue="25" />} />
        <Row label="趋势动量·缩量比例" right={<InputField type="number" defaultValue="80" suffix="%" />} />
        <Row label="默认止损偏移" right={<InputField type="number" defaultValue="5" suffix="%" />} />
        <Row label="默认止盈偏移" right={<InputField type="number" defaultValue="10" suffix="%" />} />
        <Row label="最大持仓数" right={<InputField type="number" defaultValue="3" />} />
      </CollapseCard>

      {/* 5. 风控参数 */}
      <CollapseCard title="风控参数" dotColor={colors.semantic.down}>
        <Row label="单日最大回撤" desc="触发降仓" right={<InputField type="number" defaultValue="5" suffix="%" />} />
        <Row label="极端回撤阈值" desc="触发清仓" right={<InputField type="number" defaultValue="8" suffix="%" />} />
        <Row label="最大连续亏损次数" desc="触发策略暂停" right={<InputField type="number" defaultValue="5" />} />
        <Row label="单票仓位上限" right={<InputField type="number" defaultValue="30" suffix="%" />} />
        <Row label="因子拥挤度阈值" right={<InputField type="number" defaultValue="48" suffix="%" />} />
        <Row label="极端行情阈值" desc="大盘单日跌幅" right={<InputField type="number" defaultValue="5" suffix="%" />} />
        <Row
          label=""
          right={
            <div
              style={{
                fontSize: 11,
                color: colors.semantic.up,
                lineHeight: 1.5,
                padding: "6px 0",
              }}
            >
              ⚠ 止损监视器为独立容器，不可禁用 · LIVE 金额硬编码
            </div>
          }
        />
      </CollapseCard>

      {/* 6. 交易配置 */}
      <CollapseCard title="交易配置" dotColor={colors.semantic.amber}>
        <Row label="当前模式" right={<Badge label="SIMULATION" />} />
        <Row
          label="确认模式"
          desc="建议模式 — 需用户确认后下单"
          right={
            <span style={{ fontSize: 11, color: colors.text.tertiary }}>切换</span>
          }
        />
        <Row label="miniQMT 账号" right={<span style={{ fontSize: 11, color: colors.text.tertiary }}>未配置</span>} />
        <Row label="佣金费率" right={<InputField type="number" defaultValue="2.5" suffix="万分之" />} />
        <Row label="印花税率" right={<InputField type="number" defaultValue="1" suffix="千分之" />} />
        <Row label="滑点" right={<InputField type="number" defaultValue="1" suffix="跳" />} />
        <Row
          label="LIVE 限额"
          desc="单日 50万 · 单笔 10万（硬编码）"
          right={
            <span style={{ fontSize: 11, color: colors.semantic.up }}>不可绕过</span>
          }
        />
      </CollapseCard>

      {/* ==================== 数据与推送 ==================== */}
      <GroupLabel label="数据与推送" />

      {/* 7. 数据源 */}
      <CollapseCard title="数据源" dotColor={colors.semantic.amber}>
        <Row
          label="AKShare 数据源"
          desc="免费 A 股行情数据"
          right={<Toggle checked={dsStates.akshare} onChange={() => toggleDs("akshare")} />}
        />
        <Row
          label="miniQMT 数据源"
          desc="实时行情 + 交易通道"
          right={<Toggle checked={dsStates.qmt} onChange={() => toggleDs("qmt")} />}
        />
        <Row label="miniQMT 地址" right={<InputField defaultValue="127.0.0.1" />} />
        <Row label="miniQMT 端口" right={<InputField type="number" defaultValue="10001" />} />
        <Row label="数据同步时间" desc="每日收盘后" right={<InputField defaultValue="17:00" />} />
        <Row label="舆情轮询间隔" right={<InputField type="number" defaultValue="60" suffix="分钟" />} />
      </CollapseCard>

      {/* 8. 新闻配置 */}
      <CollapseCard title="新闻配置" dotColor={colors.semantic.amber}>
        <Row
          label="华尔街见闻"
          desc="全球财经快讯"
          right={<Toggle checked={dsStates.newsWsj} onChange={() => toggleDs("newsWsj")} />}
        />
        <Row
          label="AKShare 新闻"
          desc="东方财富、新浪聚合"
          right={<Toggle checked={dsStates.newsAk} onChange={() => toggleDs("newsAk")} />}
        />
        <Row label="采集间隔" right={<InputField type="number" defaultValue="30" suffix="分钟" />} />
        <Row label="最多保留" right={<InputField type="number" defaultValue="500" suffix="条" />} />
        <Row label="热点关键词" right={<span style={{ fontSize: 11, color: colors.text.tertiary }}>降息,白酒,新能源</span>} />
      </CollapseCard>

      {/* 9. 推送通知 */}
      <CollapseCard title="推送通知" dotColor={colors.semantic.amber}>
        <Row label="🔔 风控告警" desc="告警类型、当前值、阈值" right={<Toggle checked={pushStates.risk} onChange={() => togglePush("risk")} />} />
        <Row label="🤖 Agent 精选结果" desc="每日策略运行报告" right={<Toggle checked={pushStates.agentResult} onChange={() => togglePush("agentResult")} />} />
        <Row label="📈 开仓推送" desc="标的、成交价、仓位" right={<Toggle checked={pushStates.open} onChange={() => togglePush("open")} />} />
        <Row label="📉 止损 / 止盈推送" desc="触发原因、盈亏金额" right={<Toggle checked={pushStates.stop} onChange={() => togglePush("stop")} />} />
        <Row label="📰 舆情推送" desc="事件类型、影响评估" right={<Toggle checked={pushStates.news} onChange={() => togglePush("news")} />} />
        <Row label="📊 每日复盘推送" desc="操作总结、持仓变化" right={<Toggle checked={pushStates.dailyReview} onChange={() => togglePush("dailyReview")} />} />
        <Row label="🔍 开盘前复核推送" desc="外盘波动、计划复核" right={<Toggle checked={pushStates.preMarket} onChange={() => togglePush("preMarket")} />} />
      </CollapseCard>

      {/* ==================== 高级 ==================== */}
      <GroupLabel label="高级" />

      {/* 10. 复核配置 */}
      <CollapseCard title="复核配置" dotColor={colors.text.tertiary}>
        <Row label="高开取消阈值" desc="超过此比例取消买入计划" right={<InputField type="number" defaultValue="3" suffix="%" />} />
        <Row label="低开取消阈值" desc="低于此比例取消买入计划" right={<InputField type="number" defaultValue="3" suffix="%" />} />
        <Row label="外盘波动阈值" desc="触发开盘前复核" right={<InputField type="number" defaultValue="3" suffix="%" />} />
        <Row
          label=""
          right={
            <div style={{ fontSize: 11, color: colors.text.secondary, lineHeight: 1.6, padding: "4px 0" }}>
              重大利空 → 自动清仓<br />
              一般利空 → 仓位上限降 50%<br />
              重大利好 → 推送提示
            </div>
          }
        />
      </CollapseCard>

      {/* 11. 经验库配置 */}
      <CollapseCard title="经验库配置" dotColor={colors.text.tertiary}>
        <Row label="经验衰减周期" desc="超过此时间权重逐渐降低" right={<InputField type="number" defaultValue="6" suffix="月" />} />
        <Row label="归档周期" desc="未验证的旧经验自动归档" right={<InputField type="number" defaultValue="3" suffix="月" />} />
        <Row label="市场状态权重" right={<InputField type="number" defaultValue="30" suffix="%" />} />
        <Row label="板块属性权重" right={<InputField type="number" defaultValue="25" suffix="%" />} />
        <Row label="技术形态权重" right={<InputField type="number" defaultValue="25" suffix="%" />} />
        <Row label="资金特征权重" right={<InputField type="number" defaultValue="20" suffix="%" />} />
      </CollapseCard>

      {/* 12. 系统配置 */}
      <CollapseCard title="系统配置" dotColor={colors.text.tertiary}>
        <Row label="日志级别" right={<Badge label="INFO" color={colors.semantic.amber} />} />
        <Row label="API 端口" right={<span style={{ fontSize: 12, color: colors.text.secondary, fontFamily: "monospace" }}>8000</span>} />
        <Row label="全局限流" right={<span style={{ fontSize: 12, color: colors.text.secondary }}>5 次/秒/IP</span>} />
        <Row label="备份时间" right={<InputField defaultValue="03:00" />} />
        <Row label="备份保留" right={<InputField type="number" defaultValue="30" suffix="天" />} />
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
        <Row label="粒子效果" desc="背景粒子动画" right={<Badge label="开启" />} />
        <Row
          label=""
          right={
            <div style={{ fontSize: 11, color: colors.text.tertiary, lineHeight: 1.5, padding: "4px 0" }}>
              配置存于 PostgreSQL · Redis pub/sub 热更新 · 参数变更全量日志
            </div>
          }
        />
      </CollapseCard>

      {/* ==================== 底部操作 ==================== */}
      <div style={{ marginTop: 20, marginBottom: 24 }}>
        <div
          style={{
            background: colors.bg.surface,
            borderRadius: `${colors.radius.md}px`,
            border: `1px solid ${colors.border.light}`,
            overflow: "hidden",
          }}
        >
          <Row label="版本" right={<span style={{ fontSize: 13, color: colors.text.secondary }}>1.2.0</span>} />
          <Row label="数据源" right={<span style={{ fontSize: 12, color: colors.text.tertiary }}>AKShare + miniQMT</span>} />
          <div style={{ padding: "10px 14px" }}>
            <button
              onClick={(e) => { e.stopPropagation(); handleLogout(); }}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: `${colors.radius.md}px`,
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                border: "none",
                outline: "none",
                background: colors.semantic.upBg,
                color: colors.semantic.up,
                lineHeight: 1.4,
                transition: "all 0.15s ease",
              }}
            >
              退出登录
            </button>
          </div>
        </div>
      </div>
    </div>

      <Modal
        title="修改密码"
        open={pwModalOpen}
        onCancel={() => { setPwModalOpen(false); pwForm.resetFields(); }}
        onOk={async () => {
          try {
            const values = await pwForm.validateFields();
            if (values.newPassword !== values.confirmPassword) {
              message.error("两次输入的新密码不一致");
              return;
            }
            await authService.changePassword(values.oldPassword, values.newPassword);
            message.success("密码修改成功，请重新登录");
            setPwModalOpen(false);
            pwForm.resetFields();
            // 自动登出
            useAuthStore.getState().logout();
            navigate("/login");
          } catch (err: any) {
            if (err?.errorFields) return; // form validation 内部错误，不提示
            message.error("密码修改失败：" + (err?.response?.data?.detail || err?.message || "未知错误"));
          }
        }}
        okText="确认修改"
        cancelText="取消"
      >
        <Form form={pwForm} layout="vertical">
          <Form.Item
            name="oldPassword"
            label="当前密码"
            rules={[{ required: true, message: "请输入当前密码" }]}
          >
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: "请输入新密码" },
              { min: 6, message: "密码至少6位" },
            ]}
          >
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            rules={[
              { required: true, message: "请再次输入新密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("newPassword") === value) {
                    return Promise.resolve();
                  }
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
