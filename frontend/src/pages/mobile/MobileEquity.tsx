import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { portfolioService } from "../../services/portfolioService";
import { riskService } from "../../services/riskService";
import type { PortfolioSummary } from "../../types/api-extended";
import type { RiskMetricsItem } from "../../types/api-extended";

/* ---- Mock fallback data ---- */
const MOCK_SUMMARY: PortfolioSummary = {
  total_asset: "1284350.00",
  available_cash: "298930.00",
  total_position_pct: "76.7",
  daily_pnl: "28940.00",
  unrealized_pnl: "15230.00",
  position_count: 3,
};

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

function MobileEquity() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [metrics, setMetrics] = useState<RiskMetricsItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      portfolioService.getSummary().catch(() => MOCK_SUMMARY),
      riskService.getMetrics().catch(() => MOCK_METRICS),
    ])
      .then(([s, m]) => {
        if (!cancelled) {
          setSummary(s);
          setMetrics(m);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSummary(MOCK_SUMMARY);
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
      {/* 资产概览 */}
      <MobileSectionCard title="资产概览">
        <div style={{ padding: "12px 14px" }}>
          {/* 总资产 */}
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <span style={{ fontSize: 12, color: colors.text.secondary }}>总资产</span>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: colors.text.primary,
              }}
            >
              {summary?.total_asset
                ? `${parseFloat(summary.total_asset).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                : "-"}
            </span>
          </div>

          {/* 各项指标 */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>可用现金</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: colors.text.primary }}>
                {summary?.available_cash
                  ? `${parseFloat(summary.available_cash).toLocaleString(undefined, { minimumFractionDigits: 0 })}`
                  : "-"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>持仓占比</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: colors.text.primary }}>
                {summary?.total_position_pct ?? "-"}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>持仓数量</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: colors.text.primary }}>
                {summary?.position_count ?? 0} 只
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>浮动盈亏</div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color:
                    parseFloat(summary?.unrealized_pnl ?? "0") >= 0
                      ? colors.semantic.up
                      : colors.semantic.down,
                }}
              >
                {summary?.unrealized_pnl
                  ? `${parseFloat(summary.unrealized_pnl) >= 0 ? "+" : ""}${parseFloat(summary.unrealized_pnl).toLocaleString(undefined, { minimumFractionDigits: 0 })}`
                  : "-"}
              </div>
            </div>
          </div>

          {/* 日盈亏 */}
          {summary?.daily_pnl && (
            <div
              style={{
                marginTop: 12,
                padding: "8px 12px",
                background: colors.bg.subtle,
                borderRadius: colors.radius.sm + "px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span style={{ fontSize: 12, color: colors.text.secondary }}>今日盈亏</span>
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color:
                    parseFloat(summary.daily_pnl) >= 0
                      ? colors.semantic.up
                      : colors.semantic.down,
                }}
              >
                {parseFloat(summary.daily_pnl) >= 0 ? "+" : ""}
                {parseFloat(summary.daily_pnl).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
          )}
        </div>
      </MobileSectionCard>

      {/* 风控指标 */}
      <MobileSectionCard title="风控指标">
        {latestMetrics ? (
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
              <div style={{ fontSize: 11, color: colors.text.tertiary, marginBottom: 2 }}>连亏天数</div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color:
                    latestMetrics.consecutive_loss_days > 0
                      ? colors.semantic.amber
                      : colors.text.primary,
                }}
              >
                {latestMetrics.consecutive_loss_days ?? 0} 天
              </div>
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无风控数据
          </div>
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileEquity;
