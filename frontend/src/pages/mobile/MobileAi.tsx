import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { agentService } from "../../services/agentService";
import type { AgentDiscussionItemEx } from "../../services/agentService";

/* ---- Mock fallback data ---- */
const MOCK_DISCUSSIONS: AgentDiscussionItemEx[] = [
  {
    id: 1,
    date: "2026-05-02",
    stockCode: "600519",
    roundNum: 1,
    agentName: "hunter",
    score: 92,
    buyReasons: ["量能放大突破前高", "短线动能充足"],
    againstReasons: [],
    confidence: 0.85,
    isValid: true,
    predictedOutcome: "up",
    actualOutcome: null,
    promptTokens: 1250,
    completionTokens: 320,
    modelName: "deepseek-chat",
    createdAt: "2026-05-02T10:30:00Z",
  },
  {
    id: 2,
    date: "2026-05-02",
    stockCode: "300750",
    roundNum: 1,
    agentName: "detector",
    score: 87,
    buyReasons: ["北向资金连续净流入", "板块趋势向好"],
    againstReasons: [],
    confidence: 0.78,
    isValid: true,
    predictedOutcome: "up",
    actualOutcome: null,
    promptTokens: 980,
    completionTokens: 280,
    modelName: "deepseek-chat",
    createdAt: "2026-05-02T10:35:00Z",
  },
  {
    id: 3,
    date: "2026-05-02",
    stockCode: "000858",
    roundNum: 2,
    agentName: "judge",
    score: 74,
    buyReasons: ["周期底部确认"],
    againstReasons: ["量能不足"],
    confidence: 0.62,
    isValid: true,
    predictedOutcome: "neutral",
    actualOutcome: null,
    promptTokens: 1100,
    completionTokens: 300,
    modelName: "deepseek-chat",
    createdAt: "2026-05-02T10:40:00Z",
  },
];

function MobileAi() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [discussions, setDiscussions] = useState<AgentDiscussionItemEx[]>([]);

  useEffect(() => {
    let cancelled = false;

    agentService
      .getDiscussions({ pageSize: 20 })
      .then((res) => {
        if (!cancelled) setDiscussions(res.items);
      })
      .catch(() => {
        if (!cancelled) {
          setDiscussions(MOCK_DISCUSSIONS);
          message.info("已加载模拟数据（API 暂不可用）");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const getOutcomeLabel = (outcome: string | null): string => {
    const m: Record<string, string> = {
      up: "看涨",
      down: "看跌",
      neutral: "中性",
    };
    return outcome ? m[outcome] ?? outcome : "待定";
  };

  const getOutcomeColor = (outcome: string | null): string => {
    if (outcome === "up") return colors.semantic.up;
    if (outcome === "down") return colors.semantic.down;
    return colors.text.tertiary;
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
        }}
      >
        <span style={{ fontSize: 14, color: colors.text.tertiary }}>加载中...</span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <MobileSectionCard title={`AI 分析·最近讨论 (${discussions.length})`}>
        {discussions.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无讨论数据
          </div>
        ) : (
          discussions.map((d) => (
            <div
              key={d.id}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                padding: "12px 14px",
                borderBottom: `1px solid ${colors.border.light}`,
              }}
            >
              {/* 顶行：股票代码 + Agent + 分数 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: colors.text.primary,
                    }}
                  >
                    {d.stockCode}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: colors.text.tertiary,
                      background: colors.bg.subtle,
                      padding: "1px 6px",
                      borderRadius: colors.radius.sm + "px",
                    }}
                  >
                    {d.agentName}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color:
                      d.score && d.score >= 80
                        ? colors.semantic.up
                        : d.score && d.score >= 60
                          ? colors.text.primary
                          : colors.text.tertiary,
                  }}
                >
                  {d.score ?? "-"}
                </span>
              </div>

              {/* 预测结果 + 置信度 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  fontSize: 12,
                }}
              >
                <span style={{ color: colors.text.secondary }}>
                  预测:
                </span>
                <span style={{ color: getOutcomeColor(d.predictedOutcome), fontWeight: 500 }}>
                  {getOutcomeLabel(d.predictedOutcome)}
                </span>
                <span style={{ color: colors.text.tertiary }}>|</span>
                <span style={{ color: colors.text.secondary }}>
                  置信度:{" "}
                  <span style={{ color: colors.text.primary, fontWeight: 500 }}>
                    {Math.round(d.confidence * 100)}%
                  </span>
                </span>
              </div>

              {/* 理由 */}
              {d.buyReasons.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 4,
                  }}
                >
                  {d.buyReasons.map((r, i) => (
                    <span
                      key={i}
                      style={{
                        fontSize: 11,
                        color: colors.semantic.up,
                        background: colors.semantic.upBg,
                        padding: "1px 6px",
                        borderRadius: colors.radius.sm + "px",
                      }}
                    >
                      {r}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileAi;
