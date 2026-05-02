import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import type { ExperienceItem } from "../../types/api-extended";

/* ---- Mock fallback data ---- */
const MOCK_EXPERIENCES: ExperienceItem[] = [
  {
    id: 1,
    market_state: "bull",
    strategy_type: "周期底部",
    operation: "buy",
    result: "success",
    pnl_pct: "+12.5",
    score: 92,
    confidence: 0.85,
    tags: ["量能放大", "突破前高", "主力流入"],
    created_at: "2026-05-01T10:30:00Z",
  },
  {
    id: 2,
    market_state: "sideways",
    strategy_type: "趋势低吸",
    operation: "sell",
    result: "success",
    pnl_pct: "+5.2",
    score: 78,
    confidence: 0.72,
    tags: ["获利了结", "量价背离"],
    created_at: "2026-04-28T14:20:00Z",
  },
  {
    id: 3,
    market_state: "bear",
    strategy_type: "超跌反弹",
    operation: "buy",
    result: "fail",
    pnl_pct: "-8.3",
    score: 45,
    confidence: 0.38,
    tags: ["追高风险", "流动性不足"],
    created_at: "2026-04-25T09:15:00Z",
  },
];

/* ---- Helpers ---- */
function mapOperation(op: string): string {
  const m: Record<string, string> = { buy: "买入", sell: "卖出", hold: "持有" };
  return m[op] ?? op;
}

function getResultColor(result: string): string {
  return result === "success" ? colors.semantic.up : colors.semantic.down;
}

// need colors from theme — we'll inline in component

function MobileExperience() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [experiences, setExperiences] = useState<ExperienceItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    // 后端 GET /api/v1/experience/list — 暂无独立 service，直接 fetch fallback
    // 尝试通过 api 调用
    import("../../services/api")
      .then(({ default: api }) =>
        api.get("/experience/list").then((res) => {
          if (!cancelled) {
            const data = Array.isArray(res.data) ? res.data : [];
            setExperiences(data);
          }
        }),
      )
      .catch(() => {
        if (!cancelled) {
          setExperiences(MOCK_EXPERIENCES);
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

  const getResultColor = (result: string): string => {
    return result === "success" ? colors.semantic.up : colors.semantic.down;
  };

  const getResultBg = (result: string): string => {
    return result === "success" ? colors.semantic.upBg : colors.semantic.downBg;
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
      <MobileSectionCard title={`经验库 (${experiences.length})`}>
        {experiences.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无经验数据——完成交易后经验将自动沉淀
          </div>
        ) : (
          experiences.map((exp) => {
            const actionLabel = mapOperation(exp.operation);
            const resultColor = getResultColor(exp.result);
            const resultBg = getResultBg(exp.result);

            return (
              <div
                key={exp.id}
                style={{
                  padding: "12px 14px",
                  borderBottom: `1px solid ${colors.border.light}`,
                }}
              >
                {/* 头部：日期 + 结果标签 */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      color: colors.text.tertiary,
                    }}
                  >
                    {exp.created_at?.slice(0, 10) ?? "-"}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 500,
                      color: resultColor,
                      background: resultBg,
                      padding: "1px 8px",
                      borderRadius: colors.radius.sm + "px",
                    }}
                  >
                    {exp.result === "success" ? "成功" : "失败"}
                  </span>
                </div>

                {/* 策略类型 + 市场状态 */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: colors.text.primary,
                    }}
                  >
                    {exp.strategy_type ?? "-"}
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
                    {exp.market_state ?? ""}
                  </span>
                </div>

                {/* 操作 + 盈亏 */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 500,
                      color: actionLabel === "买入" ? colors.semantic.up : colors.semantic.down,
                      background: actionLabel === "买入" ? colors.semantic.upBg : colors.semantic.downBg,
                      padding: "1px 8px",
                      borderRadius: colors.radius.sm + "px",
                    }}
                  >
                    {actionLabel}
                  </span>
                  {exp.pnl_pct && (
                    <span
                      style={{
                        fontSize: 12,
                        color: colors.text.secondary,
                      }}
                    >
                      盈亏:{" "}
                      <span
                        style={{
                          color: parseFloat(exp.pnl_pct) >= 0 ? colors.semantic.up : colors.semantic.down,
                          fontWeight: 500,
                        }}
                      >
                        {exp.pnl_pct}%
                      </span>
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: 12,
                      color: colors.text.tertiary,
                    }}
                  >
                    评分: {exp.score}
                  </span>
                </div>

                {/* 标签 */}
                {exp.tags && exp.tags.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                    }}
                  >
                    {exp.tags.map((tag, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: 11,
                          color: colors.text.secondary,
                          background: colors.bg.subtle,
                          padding: "1px 6px",
                          borderRadius: colors.radius.sm + "px",
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileExperience;
