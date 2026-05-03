import { useMemo, useEffect, useState } from "react";
import { Row, Col, Card, Typography, Statistic, Space, Spin } from "antd";
import ReactECharts from "echarts-for-react";
import { colors } from "../../theme/colors";
import { portfolioService } from "../../services/portfolioService";
import type { PortfolioSummary } from "../../types/api-extended";

const { Title, Text } = Typography;

// ─── Component ───────────────────────────────────────────────────────────────

const EquityCurvePage: React.FC = () => {
  const navData = useMemo(() => ({ dates: [] as string[], values: [] as number[] }), []);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portfolioService.getSummary()
      .then((data) => {
        setSummary(data);
      })
      .catch((err) => {
        console.error("Failed to load portfolio summary:", err);
        console.warn("加载统计数据失败，使用演示数据");
      })
      .finally(() => setLoading(false));
  }, []);

  // Derive stats from PortfolioSummary if available, else return 0
  const stats = useMemo(() => {
    if (!summary) return { totalReturn: 0, annualReturn: 0, maxDrawdown: 0, sharpeRatio: 0 };
    const totalAsset = summary.total_asset ? parseFloat(summary.total_asset) : 0;
    // Approximate return from daily_pnl / total_asset (rough estimate)
    // This is a placeholder — real metrics need a dedicated API
    return {
      totalReturn: totalAsset > 0 ? ((summary.daily_pnl ? parseFloat(summary.daily_pnl) : 0) / totalAsset) * 100 : 0,
      annualReturn: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
    };
  }, [summary]);

  const chartOption = useMemo(
    () => ({
      backgroundColor: "transparent",
      grid: { left: 48, right: 16, top: 24, bottom: 60 },
      xAxis: {
        type: "category" as const,
        data: navData.dates,
        axisLine: { lineStyle: { color: colors.border } },
        axisLabel: {
          color: colors.muted,
          fontSize: 11,
          formatter: (v: string) => v.slice(5),
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        splitLine: { lineStyle: { color: colors.border, type: "dashed" as const } },
        axisLabel: { color: colors.muted, fontSize: 11 },
      },
      series: [
        {
          type: "line" as const,
          data: navData.values,
          smooth: true,
          symbol: "none",
          lineStyle: { color: colors.gold, width: 2 },
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(240, 192, 64, 0.4)" },
                { offset: 1, color: "rgba(240, 192, 64, 0.02)" },
              ],
            },
          },
        },
      ],
      dataZoom: [
        {
          type: "inside" as const,
          start: 0,
          end: 100,
        },
        {
          type: "slider" as const,
          start: 0,
          end: 100,
          height: 20,
          bottom: 8,
          borderColor: colors.border,
          fillerColor: "rgba(240, 192, 64, 0.25)",
          handleStyle: { color: colors.gold },
          textStyle: { color: colors.muted, fontSize: 10 },
        },
      ],
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: colors.surface,
        borderColor: colors.border,
        textStyle: { color: colors.text, fontSize: 12 },
        formatter: (params: { value: number }[]) => {
          if (!params || !params[0]) return "";
          return `净值: ${params[0].value.toFixed(4)}`;
        },
      },
    }),
    [navData]
  );

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        星轨 — 净值曲线
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总收益</span>}
              value={stats.totalReturn}
              suffix="%"
              precision={2}
              valueStyle={{ color: colors.gold, fontSize: 18, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>年化收益</span>}
              value={stats.annualReturn}
              suffix="%"
              precision={2}
              valueStyle={{ color: colors.gold, fontSize: 18, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>最大回撤</span>}
              value={stats.maxDrawdown}
              suffix="%"
              precision={2}
              valueStyle={{ color: colors.success, fontSize: 18, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>夏普比率</span>}
              value={stats.sharpeRatio}
              precision={2}
              valueStyle={{ color: colors.shard, fontSize: 18, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 净值曲线 */}
      <Card
        size="small"
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: "12px 16px" } }}
      >
        <Space style={{ marginBottom: 8 }}>
          <Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>
            净值走势
          </Text>
          <Text style={{ color: colors.dimmed, fontSize: 12 }}>
            2026/01 - 2026/04
          </Text>
        </Space>
        <ReactECharts option={chartOption} style={{ height: 400 }} notMerge />
      </Card>
    </div>
  );
};

export default EquityCurvePage;
