import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import { agentService } from "../../services/agentService";
import type { AgentDecisionItemEx, AgentDiscussionItemEx } from "../../services/agentService";

/* ---- Signal display helper ---- */
interface SignalItem {
  code: string;
  name: string;
  strategy: string;
  score: number;
  price: string;
  change: string;
  changeUp: boolean;
}

/** 将后端 Decision 转为前端展示格式（暂缺 name/price/change，后端没返回） */
function decisionToSignal(d: AgentDecisionItemEx): SignalItem {
  return {
    code: d.stockCode,
    name: d.stockCode,            // 后端未返回 name，暂时显示 code
    strategy: d.decisionReason.slice(0, 12) || d.decision,
    score: d.totalScore,
    price: "--",
    change: d.decision === "buy" ? "建议买入" : "观望/卖出",
    changeUp: d.decision === "buy",
  };
}

/** 将后端 Discussion 转为 AgentBubble 格式 */
function discussionToBubble(d: AgentDiscussionItemEx) {
  const agent = d.agentName.toLowerCase();
  const agentType = agent.includes("hunter")
    ? "hunter"
    : agent.includes("detector")
      ? "detector"
      : "judge";
  const reasons = [...d.buyReasons, ...d.againstReasons];
  return {
    agent: agentType as "hunter" | "detector" | "judge",
    name: d.agentName,
    text: reasons.length > 0 ? reasons.join("；") : `评分 ${d.score ?? "--"}，信心 ${(d.confidence * 100).toFixed(0)}%`,
  };
}

function MobileDashboard() {
  const { message } = App.useApp();
  const { colors } = useTheme();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [summary, setSummary] = useState<Record<string, any> | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [tradeMode, setTradeMode] = useState<Record<string, any> | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [marketState, setMarketState] = useState<Record<string, any> | null>(null);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [discussions, setDiscussions] = useState<Array<{
    agent: "hunter" | "detector" | "judge";
    name: string;
    text: string;
  }>>([]);

  const loadData = useCallback(async () => {
    const results = await Promise.all([
      portfolioService.getSummary().catch(() => null),
      tradeService.getMode().catch(() => null),
      marketService.getMarketState().catch(() => null),
      agentService.getDecisions({ pageSize: 3 }).catch(() => null),
      agentService.getDiscussions({ pageSize: 3 }).catch(() => null),
    ]);

    const [s, m, ms, decisionsResult, discussionsResult] = results;
    setSummary(s);
    setTradeMode(m);
    setMarketState(ms);

    if (decisionsResult && decisionsResult.decisions.length > 0) {
      setSignals(decisionsResult.decisions.map(decisionToSignal));
    } else {
      setSignals([]);
    }

    if (discussionsResult && discussionsResult.items.length > 0) {
      setDiscussions(discussionsResult.items.map(discussionToBubble));
    } else {
      setDiscussions([]);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    loadData().finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [loadData]);

  const handleSignalClick = useCallback(
    (code: string) => {
      const sig = signals.find((s) => s.code === code);
      if (sig) {
        message.info(`${code} · 评分 ${sig.score} · ${sig.change}`);
      } else {
        message.info(`${code} — 查看详情`);
      }
    },
    [message, signals],
  );

  const handleRefresh = useCallback(() => {
    message.info("刷新数据中...");
    setLoading(true);
    loadData().finally(() => setLoading(false));
  }, [message, loadData]);

  const handleViewAllSignals = useCallback(() => {
    navigate("/m/stock-pool");
  }, [navigate]);

  const handleViewAllDiscussion = useCallback(() => {
    navigate("/m/ai");
  }, [navigate]);

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
              value={`¥${summary?.total_asset != null ? Number(summary.total_asset).toLocaleString() : "0"}`}
              change={{ text: "+2.3% 今日", type: "up" }}
            />
            <MobileMetricCard
              label="今日盈亏"
              value={`+¥${summary?.daily_pnl != null ? Number(summary.daily_pnl).toLocaleString() : "0"}`}
              change={{ text: "+1.8%", type: "up" }}
              valueColor={colors.semantic.up}
            />
            <MobileMetricCard
              label="活跃信号"
              value={`${signals.length}`}
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
                  onClick={() => handleSignalClick(sig.code)}
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
