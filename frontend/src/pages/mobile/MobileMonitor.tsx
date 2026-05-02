import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { riskService } from "../../services/riskService";
import type { RiskEventItem, RiskMetricsItem } from "../../types/api-extended";

/* ---- Mock fallback data ---- */
const MOCK_EVENTS: RiskEventItem[] = [
  {
    id: 1,
    event_type: "止损触发",
    event_level: "warning",
    trigger_reason: "宁德时代(300750) 日内跌幅 5.2%，超过 5% 止损线",
    action_taken: "自动平仓 200 股",
    trade_date: "2026-05-02",
    created_at: "2026-05-02T14:30:00Z",
  },
  {
    id: 2,
    event_type: "集中度预警",
    event_level: "info",
    trigger_reason: "消费电子板块持仓占比 42%，超过 30% 阈值",
    action_taken: "发送预警通知",
    trade_date: "2026-05-02",
    created_at: "2026-05-02T09:15:00Z",
  },
  {
    id: 3,
    event_type: "波动率异常",
    event_level: "critical",
    trigger_reason: "上证指数 30 分钟波动率 3.8%，超过 3% 阈值",
    action_taken: "暂停新开仓",
    trade_date: "2026-05-01",
    created_at: "2026-05-01T10:45:00Z",
  },
];

const MOCK_METRICS: RiskMetricsItem[] = [
  {
    trade_date: "2026-05-02",
    daily_drawdown: "2.3",
    win_rate: "68.5",
    consecutive_loss_days: 0,
    total_position_pct: "76.7",
    risk_status: "normal",
  },
];

/* ---- Helpers ---- */
function getLevelColor(level: string): string {
  const m: Record<string, string> = {
    critical: colors.semantic.up,
    warning: colors.semantic.amber,
    info: colors.text.secondary,
  };
  return m[level] ?? colors.text.secondary;
}

function getLevelBg(level: string): string {
  const m: Record<string, string> = {
    critical: colors.semantic.upBg,
    warning: colors.semantic.amberBg,
    info: colors.bg.subtle,
  };
  return m[level] ?? colors.bg.subtle;
}

function getLevelLabel(level: string): string {
  const m: Record<string, string> = {
    critical: "严重",
    warning: "警告",
    info: "提示",
  };
  return m[level] ?? level;
}

function MobileMonitor() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<RiskEventItem[]>([]);
  const [metrics, setMetrics] = useState<RiskMetricsItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      riskService.getEvents().catch(() => MOCK_EVENTS),
      riskService.getMetrics().catch(() => MOCK_METRICS),
    ])
      .then(([e, m]) => {
        if (!cancelled) {
          setEvents(e);
          setMetrics(m);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvents(MOCK_EVENTS);
          setMetrics(MOCK_METRICS);
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

  const latestMetrics = metrics.length > 0 ? metrics[metrics.length - 1] : null;

  return (
    <div
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
