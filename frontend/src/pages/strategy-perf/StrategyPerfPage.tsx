import { useEffect, useState } from "react";
import { App, Row, Col, Card, Statistic, Typography, Table, Tag, Space, Spin } from "antd";
import { colors } from "../../theme/colors";
import { strategyService } from "../../services/strategyService";
import { tradeService } from "../../services/tradeService";
import type { BacktestResultItem } from "../../types/api-extended";
import type { OrderResponse } from "../../types/api-extended";

const { Title, Text } = Typography;

// ─── Mock Data (fallback) — TODO: remove once API returns real data ──────────

const fallbackStrategy1Stats = {
  winRate: 62.5,
  totalTrades: 168,
  profitLossRatio: 1.85,
  maxDrawdown: -6.32,
  sharpeRatio: 1.42,
};

const fallbackStrategy2Stats = {
  winRate: 55.8,
  totalTrades: 134,
  profitLossRatio: 1.53,
  maxDrawdown: -8.17,
  sharpeRatio: 0.98,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const strategyLabels: Record<string, string> = {
  trend_following: "趋势跟踪",
  value_reversion: "价值回归",
};

function dirTag(dir: string) {
  return (
    <Tag color={dir === "buy" ? colors.danger : colors.success} style={{ borderRadius: 4, margin: 0 }}>
      {dir === "buy" ? "买入" : "卖出"}
    </Tag>
  );
}

const tradeColumns = [
  {
    title: "日期",
    dataIndex: "created_at",
    key: "created_at",
    render: (v: string) => <Text style={{ color: colors.muted }}>{v?.slice(0, 10) ?? "-"}</Text>,
  },
  {
    title: "标的",
    key: "stock",
    render: (_: unknown, r: OrderResponse) => (
      <Space size={4}>
        <Text style={{ color: colors.text, fontWeight: 500 }}>{r.stock_code}</Text>
      </Space>
    ),
  },
  {
    title: "操作",
    dataIndex: "direction",
    key: "direction",
    align: "center" as const,
    render: (v: string) => dirTag(v),
  },
  {
    title: "价格",
    dataIndex: "price",
    key: "price",
    align: "right" as const,
    render: (v: string | number | null | undefined) => (
      <Text style={{ color: colors.text }}>¥ {Number(v ?? 0).toFixed(2)}</Text>
    ),
  },
  {
    title: "数量",
    dataIndex: "volume",
    key: "volume",
    align: "right" as const,
    render: (v: number) => <Text style={{ color: colors.text }}>{v?.toLocaleString() ?? "-"}</Text>,
  },
  {
    title: "状态",
    dataIndex: "status",
    key: "status",
    align: "center" as const,
    render: (v: string) => (
      <Tag style={{ borderRadius: 4, margin: 0 }}>{v}</Tag>
    ),
  },
];

// ─── Helpers to extract stats from BacktestResultItem ───────────────────────

function extractStats(item: BacktestResultItem) {
  return {
    winRate: item.win_rate ? parseFloat(item.win_rate) : 0,
    totalTrades: item.total_trades ?? 0,
    profitLossRatio: item.profit_loss_ratio ? parseFloat(item.profit_loss_ratio) : 0,
    maxDrawdown: item.max_drawdown ? parseFloat(item.max_drawdown) : 0,
    sharpeRatio: 0, // backtest results don't include sharpe
  };
}

// ─── Stat Card Sub-component ────────────────────────────────────────────────

function StatCards({ stats, title }: { stats: typeof fallbackStrategy1Stats; title: string }) {
  return (
    <>
      <Title level={5} style={{ color: colors.text, marginBottom: 12 }}>
        {title}
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>胜率</span>}
              value={stats.winRate}
              suffix="%"
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总交易次数</span>}
              value={stats.totalTrades}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>盈亏比</span>}
              value={stats.profitLossRatio}
              valueStyle={{ color: colors.gold, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>最大回撤</span>}
              value={stats.maxDrawdown}
              suffix="%"
              valueStyle={{ color: colors.success, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>夏普比率</span>}
              value={stats.sharpeRatio}
              valueStyle={{ color: colors.shard, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────

const StrategyPerfPage: React.FC = () => {
  const { message } = App.useApp();
  const [backtestResults, setBacktestResults] = useState<BacktestResultItem[]>([]);
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      strategyService.getBacktestResults(),
      tradeService.getOrders(),
    ])
      .then(([results, orderList]) => {
        setBacktestResults(results);
        setOrders(orderList);
      })
      .catch((err) => {
        console.error("Failed to load strategy perf data:", err);
        message.error("加载策略绩效数据失败，使用演示数据");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  // Group backtest results by strategy_type
  const strategy1Result = backtestResults.find((r) => r.strategy_type === "trend_following");
  const strategy2Result = backtestResults.find((r) => r.strategy_type === "value_reversion");

  const s1Stats = strategy1Result ? extractStats(strategy1Result) : fallbackStrategy1Stats;
  const s2Stats = strategy2Result ? extractStats(strategy2Result) : fallbackStrategy2Stats;

  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        修行日记 — 策略绩效统计
      </Title>

      <StatCards stats={s1Stats} title={`策略一 · ${strategyLabels.trend_following ?? "趋势跟踪"}`} />
      <StatCards stats={s2Stats} title={`策略二 · ${strategyLabels.value_reversion ?? "价值回归"}`} />

      {/* 历史交易记录 */}
      <Title level={5} style={{ color: colors.text, marginBottom: 12 }}>
        历史交易记录
      </Title>
      <Card
        size="small"
        style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={orders}
          columns={tradeColumns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: "transparent" }}
          locale={{ emptyText: "暂无交易记录" }}
        />
      </Card>
    </div>
  );
};

export default StrategyPerfPage;
