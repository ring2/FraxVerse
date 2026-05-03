import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { riskService } from "../../services/riskService";
import type { RiskEventItem, RiskMetricsItem } from "../../types/api-extended";

function MobileMonitor() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<RiskEventItem[]>([]);
  const [metrics, setMetrics] = useState<RiskMetricsItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      riskService.getEvents().catch(() => []),
      riskService.getMetrics().catch(() => []),
    ])
      .then(([e, m]) => {
        if (!cancelled) {
          setEvents(e);
          setMetrics(m);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvents([]);
          setMetrics([]);
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

  /* ---- Inline helpers (use colors from useTheme) ---- */
  const getLevelColor = (level: string): string => {
    const m: Record<string, string> = {
      critical: colors.semantic.up,
      warning: colors.semantic.amber,
      info: colors.text.secondary,
    };
    return m[level] ?? colors.text.secondary;
  };

  const getLevelBg = (level: string): string => {
    const m: Record<string, string> = {
      critical: colors.semantic.upBg,
      warning: colors.semantic.amberBg,
      info: colors.bg.subtle,
    };
    return m[level] ?? colors.bg.subtle;
  };

  const getLevelLabel = (level: string): string => {
    const m: Record<string, string> = {
      critical: "严重",
      warning: "警告",
      info: "提示",
    };
    return m[level] ?? level;
  };

  if (loading) {
    return (
      <div className="page-enter"
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

  const latestMetrics = metrics.length > 0 ? metrics[metrics.length - 1] : null;

  return (
    <div className="page-enter"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* 风控概览 */}
      {latestMetrics && (
        <MobileSectionCard title="风控概览">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
              padding: "12px 14px",
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>风控状态</div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color:
                    latestMetrics.risk_status === "normal"
                      ? colors.semantic.down
                      : colors.semantic.amber,
                }}
              >
                {latestMetrics.risk_status === "normal" ? "正常" : "警戒"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>日回撤</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>
                {latestMetrics.daily_drawdown ?? "-"}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>胜率</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>
                {latestMetrics.win_rate ?? "-"}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>持仓占比</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>
                {latestMetrics.total_position_pct ?? "-"}%
              </div>
            </div>
          </div>
        </MobileSectionCard>
      )}

      {/* 风控事件列表 */}
      <MobileSectionCard title={`风控事件 (${events.length})`}>
        {events.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无风控事件
          </div>
        ) : (
          events.map((evt) => (
            <div
              key={evt.id}
              style={{
                padding: "12px 14px",
                borderBottom: `1px solid ${colors.border.light}`,
              }}
            >
              {/* 头部：事件类型 + 级别 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 6,
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
                      fontSize: 13,
                      fontWeight: 600,
                      color: colors.text.primary,
                    }}
                  >
                    {evt.event_type}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: getLevelColor(evt.event_level),
                      background: getLevelBg(evt.event_level),
                      padding: "1px 6px",
                      borderRadius: colors.radius.sm + "px",
                      fontWeight: 500,
                    }}
                  >
                    {getLevelLabel(evt.event_level)}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    color: colors.text.tertiary,
                  }}
                >
                  {evt.created_at?.slice(0, 16).replace("T", " ") ?? ""}
                </span>
              </div>

              {/* 触发原因 */}
              <div
                style={{
                  fontSize: 12,
                  color: colors.text.secondary,
                  lineHeight: 1.6,
                  marginBottom: 4,
                }}
              >
                {evt.trigger_reason}
              </div>

              {/* 处置措施 */}
              <div
                style={{
                  fontSize: 11,
                  color: colors.text.tertiary,
                }}
              >
                处置: {evt.action_taken}
              </div>
            </div>
          ))
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileMonitor;
