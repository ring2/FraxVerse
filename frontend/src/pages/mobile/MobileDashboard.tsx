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

  const handleRefresh = useCallback(() => {
    message.info("刷新数据中...");
    setLoading(true);
    Promise.all([
      portfolioService.getSummary().catch(() => MOCK_SUMMARY),
      tradeService.getMode().catch(() => MOCK_TRADE_MODE),
      marketService.getMarketState().catch(() => MOCK_MARKET_STATE),
    ])
      .then(([s, m, ms]) => {
        setSummary(s);
        setTradeMode(m);
        setMarketState(ms);
      })
      .catch(() => {
        setSummary(MOCK_SUMMARY);
        setTradeMode(MOCK_TRADE_MODE);
        setMarketState(MOCK_MARKET_STATE);
      })
      .finally(() => setLoading(false));
  }, [message]);

  const handleViewAllSignals = useCallback(() => {
    message.info("查看全部信号 — 开发中");
  }, [message]);

  const handleViewAllDiscussion = useCallback(() => {
    message.info("AI 分析详情 — 开发中");
  }, [message]);

  const signals = MOCK_SIGNALS;
  const discussions = MOCK_AGENT_DISCUSSIONS;

  const mode = tradeMode?.current_mode ?? "SIMULATION";

  return (
    <div className="page-enter">
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
        <span
          style={{
            background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          看盘
        </span>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 6,
            alignItems: "center",
          }}
        >
          {/* 刷新按钮 */}
          <button
            onClick={handleRefresh}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: 10,
              cursor: "pointer",
              border: "none",
              outline: "none",
              background: "transparent",
              color: colors.text.secondary,
              transition: "all 0.2s ease",
              fontSize: 16,
              lineHeight: 1,
              padding: 0,
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = colors.purple[50];
              (e.currentTarget as HTMLElement).style.color = colors.purple[500];
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.color = colors.text.secondary;
            }}
            title="刷新数据"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </button>
          {/* 交易模式标签 */}
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
              color: colors.purple[500],
              gap: 4,
            }}
          >
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: colors.purple[500], display: "inline-block" }} />
            {mode}
          </span>
          {/* 市场状态标签 */}
          {marketState && (
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
                color: colors.semantic.up,
                gap: 4,
              }}
            >
              🐂 {marketState.main_line_sector || "牛市"}
            </span>
          )}
        </div>
      </div>

      {loading ? (
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
      ) : (
        <>
          {/* ===== 指标卡片网格 (2列) ===== */}
          <div
            className="stagger"
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
            <MobileSectionCard title="今日交易信号" showLink onClickLink={handleViewAllSignals}>
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
                    transition: "background 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      colors.bg.subtle;
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      "transparent";
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
          <MobileSectionCard title="AI 分析·最新讨论" showLink onClickLink={handleViewAllDiscussion}>
            {discussions.map((d, idx) => (
              <MobileAgentBubble
                key={idx}
                agent={d.agent}
                name={d.name}
                text={d.text}
              />
            ))}
          </MobileSectionCard>
        </>
      )}
    </div>
  );
}

export default MobileDashboard;
