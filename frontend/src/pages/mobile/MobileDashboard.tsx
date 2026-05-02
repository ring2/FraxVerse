import { useCallback, useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
  MobileAgentBubble,
} from "../../components/mobile";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";
import { marketService } from "../../services/marketService";

/* ---- Mock fallback data ---- */
const MOCK_SUMMARY = {
  total_asset: 1284350,
  available_cash: 298930,
  daily_pnl: 28940,
  daily_pnl_pct: 2.3,
  position_count: 3,
  total_position_pct: 76.7,
};

const MOCK_TRADE_MODE = { current_mode: "SIMULATION" };

const MOCK_MARKET_STATE = { current_state: "bull", main_line_sector: "消费电子" };

const MOCK_SIGNALS = [
  {
    code: "600519",
    name: "贵州茅台",
    strategy: "周期底部",
    score: 92,
    price: "1,680.50",
    change: "+3.2%",
    changeUp: true,
  },
  {
    code: "300750",
    name: "宁德时代",
    strategy: "趋势低吸",
    score: 87,
    price: "218.30",
    change: "+2.1%",
    changeUp: true,
  },
  {
    code: "000858",
    name: "五粮液",
    strategy: "周期底部",
    score: 74,
    price: "156.80",
    change: "+1.5%",
    changeUp: true,
  },
];

const MOCK_AGENT_DISCUSSIONS = [
  { agent: "hunter" as const, name: "Hunter 猎手", text: "茅台量能放大，突破前高压力位，短线动能充足" },
  { agent: "detector" as const, name: "Detector 侦探", text: "北向资金连续3日净流入，偏好消费板块" },
  { agent: "judge" as const, name: "Judge 法官", text: "综合评分92，周期底部确认，建议纳入观察" },
];

function MobileDashboard() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [summary, setSummary] = useState<Record<string, any> | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [tradeMode, setTradeMode] = useState<Record<string, any> | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [marketState, setMarketState] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      portfolioService.getSummary().catch(() => MOCK_SUMMARY),
      tradeService.getMode().catch(() => MOCK_TRADE_MODE),
      marketService.getMarketState().catch(() => MOCK_MARKET_STATE),
    ])
      .then(([s, m, ms]) => {
        if (cancelled) return;
        setSummary(s);
        setTradeMode(m);
        setMarketState(ms);
      })
      .catch(() => {
        if (!cancelled) {
          setSummary(MOCK_SUMMARY);
          setTradeMode(MOCK_TRADE_MODE);
          setMarketState(MOCK_MARKET_STATE);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSignalClick = useCallback(() => {
    message.info("查看详情 — 开发中");
  }, [message]);

  const signals = MOCK_SIGNALS;
  const discussions = MOCK_AGENT_DISCUSSIONS;

  const marketTag = marketState
    ? marketState.current_state === "bull"
      ? { label: "🐂 牛市", color: colors.semantic.up }
      : marketState.current_state === "bear"
      ? { label: "🐻 熊市", color: colors.semantic.down }
      : { label: "⚖️ 震荡", color: colors.semantic.amber }
    : { label: "⏳ 加载中", color: colors.text.tertiary };

  const mode = tradeMode?.current_mode ?? "SIMULATION";
  const modeTagColor =
    mode === "LIVE"
      ? colors.semantic.up
      : mode === "PAPER"
      ? colors.semantic.amber
      : colors.purple[500];

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 200,
        }}
      >
        <span style={{ color: colors.text.tertiary, fontSize: 14 }}>
          加载中...
        </span>
      </div>
    );
  }

  return (
    <div>
      {/* ===== 标题栏 ===== */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontSize: 18,
          fontWeight: 600,
          color: colors.text.primary,
          marginBottom: 14,
          lineHeight: 1.3,
        }}
      >
        看盘
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 6,
            alignItems: "center",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              fontSize: 11,
              fontWeight: 500,
              lineHeight: 1.3,
              padding: "3px 10px",
              borderRadius: 20,
              backgroundColor: colors.semantic.upBg,
              color: modeTagColor,
            }}
          >
            {mode}
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              fontSize: 11,
              fontWeight: 500,
              lineHeight: 1.3,
              padding: "3px 10px",
              borderRadius: 20,
              backgroundColor: colors.semantic.upBg,
              color: marketTag.color,
            }}
          >
            {marketTag.label}
          </span>
        </div>
      </div>

      {/* ===== 指标卡片网格 (2列) ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <MobileMetricCard
          label="总资产"
          value={`¥${summary?.total_asset != null ? Number(summary.total_asset).toLocaleString() : "1,284,350"}`}
          change={{ text: "+2.3% 今日", type: "up" }}
        />
        <MobileMetricCard
          label="今日盈亏"
          value={`+¥${summary?.daily_pnl != null ? Number(summary.daily_pnl).toLocaleString() : "28,940"}`}
          change={{ text: "+1.8%", type: "up" }}
          valueColor={colors.semantic.up}
        />
        <MobileMetricCard
          label="活跃信号"
          value="12"
          change={{ text: "3 待审", type: "neutral" }}
          valueColor={colors.purple[500]}
        />
        <MobileMetricCard
          label="经验库"
          value="247"
          change={{ text: "2 失败经验", type: "down" }}
        />
      </div>

      {/* ===== 今日交易信号 ===== */}
      <div style={{ marginBottom: 16 }}>
        <MobileSectionCard title="今日交易信号">
          {signals.map((sig, idx) => (
            <div
              key={idx}
              onClick={handleSignalClick}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                cursor: "pointer",
                borderBottom:
                  idx < signals.length - 1
                    ? `1px solid ${colors.border.light}`
                    : "none",
                transition: "background 0.15s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  colors.bg.subtle;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              {/* 左侧：代码 + 名称 */}
              <div style={{ minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: colors.text.primary,
                    lineHeight: 1.4,
                  }}
                >
                  {sig.code}
                  <span
                    style={{
                      fontSize: 12,
                      color: colors.text.tertiary,
                      marginLeft: 6,
                    }}
                  >
                    {sig.name}
                  </span>
                </div>
                <div style={{ marginTop: 4 }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      fontSize: 11,
                      fontWeight: 500,
                      lineHeight: 1.3,
                      padding: "2px 8px",
                      borderRadius: 20,
                      backgroundColor: colors.semantic.amberBg,
                      color: colors.semantic.amber,
                    }}
                  >
                    {sig.strategy}
                  </span>
                </div>
              </div>

              {/* 右侧：评分 + 现价 + 涨跌 */}
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: colors.text.primary,
                    lineHeight: 1.4,
                  }}
                >
                  评分 {sig.score}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: colors.text.secondary,
                    lineHeight: 1.3,
                    marginTop: 2,
                  }}
                >
                  {sig.price}
                  <span
                    style={{
                      marginLeft: 4,
                      color: sig.changeUp
                        ? colors.semantic.up
                        : colors.semantic.down,
                    }}
                  >
                    {sig.change}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </MobileSectionCard>
      </div>

      {/* ===== AI 分析·最新讨论 ===== */}
      <MobileSectionCard title="AI 分析·最新讨论">
        {discussions.map((d, idx) => (
          <MobileAgentBubble
            key={idx}
            agent={d.agent}
            name={d.name}
            text={d.text}
          />
        ))}
      </MobileSectionCard>
    </div>
  );
}

export default MobileDashboard;
