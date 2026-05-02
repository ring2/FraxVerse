import { Row, Col, Card, Statistic, Typography, Table, Tag, Space } from "antd";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

const strategy1Stats = {
  winRate: 62.5,
  totalTrades: 168,
  profitLossRatio: 1.85,
  maxDrawdown: -6.32,
  sharpeRatio: 1.42,
};

const strategy2Stats = {
  winRate: 55.8,
  totalTrades: 134,
  profitLossRatio: 1.53,
  maxDrawdown: -8.17,
  sharpeRatio: 0.98,
};

interface TradeRecord {
  id: string;
  date: string;
  stockName: string;
  stockCode: string;
  direction: "buy" | "sell";
  price: number;
  volume: number;
  pnl: number;
  pnlPct: number;
}

const strategy1Trades: TradeRecord[] = [
  { id: "s1-1", date: "2026-04-28", stockName: "贵州茅台", stockCode: "600519", direction: "buy", price: 185.5, volume: 1200, pnl: 15720, pnlPct: 7.06 },
  { id: "s1-2", date: "2026-04-25", stockName: "宁德时代", stockCode: "300750", direction: "sell", price: 72.15, volume: 3500, pnl: 13825, pnlPct: 5.79 },
  { id: "s1-3", date: "2026-04-22", stockName: "中国平安", stockCode: "601318", direction: "buy", price: 52.8, volume: 2800, pnl: -4984, pnlPct: -3.37 },
  { id: "s1-4", date: "2026-04-18", stockName: "招商银行", stockCode: "600036", direction: "sell", price: 38.6, volume: 5000, pnl: 8900, pnlPct: 4.83 },
  { id: "s1-5", date: "2026-04-15", stockName: "五粮液", stockCode: "000858", direction: "buy", price: 142.3, volume: 800, pnl: -2180, pnlPct: -1.92 },
];

const strategy2Trades: TradeRecord[] = [
  { id: "s2-1", date: "2026-04-29", stockName: "迈瑞医疗", stockCode: "300760", direction: "buy", price: 268.5, volume: 600, pnl: 7230, pnlPct: 4.49 },
  { id: "s2-2", date: "2026-04-26", stockName: "立讯精密", stockCode: "002475", direction: "sell", price: 35.2, volume: 8000, pnl: 10400, pnlPct: 3.87 },
  { id: "s2-3", date: "2026-04-23", stockName: "隆基绿能", stockCode: "601012", direction: "buy", price: 28.6, volume: 10000, pnl: -6520, pnlPct: -2.28 },
  { id: "s2-4", date: "2026-04-19", stockName: "药明康德", stockCode: "603259", direction: "sell", price: 58.4, volume: 3200, pnl: 5880, pnlPct: 3.25 },
  { id: "s2-5", date: "2026-04-16", stockName: "东方财富", stockCode: "300059", direction: "buy", price: 22.8, volume: 15000, pnl: -3750, pnlPct: -1.10 },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function valColor(v: number): string {
  if (v > 0) return colors.gold;
  if (v < 0) return colors.danger;
  return colors.text;
}

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
    dataIndex: "date",
    key: "date",
    render: (v: string) => <Text style={{ color: colors.muted }}>{v}</Text>,
  },
  {
    title: "标的",
    key: "stock",
    render: (_: unknown, r: TradeRecord) => (
      <Space size={4}>
        <Text style={{ color: colors.text, fontWeight: 500 }}>{r.stockName}</Text>
        <Text style={{ color: colors.dimmed, fontSize: 12 }}>{r.stockCode}</Text>
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
    render: (v: number) => <Text style={{ color: colors.text }}>¥ {v.toFixed(2)}</Text>,
  },
  {
    title: "数量",
    dataIndex: "volume",
    key: "volume",
    align: "right" as const,
    render: (v: number) => <Text style={{ color: colors.text }}>{v.toLocaleString()}</Text>,
  },
  {
    title: "盈亏",
    dataIndex: "pnl",
    key: "pnl",
    align: "right" as const,
    render: (v: number) => (
      <Text style={{ color: valColor(v), fontWeight: 600 }}>
        {v > 0 ? "+" : ""}¥ {v.toLocaleString()}
      </Text>
    ),
  },
  {
    title: "盈亏%",
    dataIndex: "pnlPct",
    key: "pnlPct",
    align: "right" as const,
    render: (v: number) => (
      <Text style={{ color: valColor(v), fontWeight: 600 }}>
        {v > 0 ? "+" : ""}{v.toFixed(2)}%
      </Text>
    ),
  },
];

// ─── Component ───────────────────────────────────────────────────────────────

const StrategyPerfPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        修行日记 — 策略绩效统计
      </Title>

      {/* 策略一统计卡片 */}
      <Title level={5} style={{ color: colors.nebula, marginBottom: 12 }}>
        策略一 · 趋势跟踪
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>胜率</span>}
              value={strategy1Stats.winRate}
              suffix="%"
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总交易次数</span>}
              value={strategy1Stats.totalTrades}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>盈亏比</span>}
              value={strategy1Stats.profitLossRatio}
              valueStyle={{ color: colors.gold, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>最大回撤</span>}
              value={strategy1Stats.maxDrawdown}
              suffix="%"
              valueStyle={{ color: colors.success, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>夏普比率</span>}
              value={strategy1Stats.sharpeRatio}
              valueStyle={{ color: colors.shard, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 策略一交易记录 */}
      <Card
        size="small"
        title={<Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>策略一 · 历史交易记录</Text>}
        style={{ background: colors.card, borderColor: colors.border, borderRadius: 8, marginBottom: 24 }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={strategy1Trades}
          columns={tradeColumns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: "transparent" }}
        />
      </Card>

      {/* 策略二统计卡片 */}
      <Title level={5} style={{ color: colors.shard, marginBottom: 12 }}>
        策略二 · 价值回归
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>胜率</span>}
              value={strategy2Stats.winRate}
              suffix="%"
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总交易次数</span>}
              value={strategy2Stats.totalTrades}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>盈亏比</span>}
              value={strategy2Stats.profitLossRatio}
              valueStyle={{ color: colors.gold, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>最大回撤</span>}
              value={strategy2Stats.maxDrawdown}
              suffix="%"
              valueStyle={{ color: colors.success, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}>
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>夏普比率</span>}
              value={strategy2Stats.sharpeRatio}
              valueStyle={{ color: colors.shard, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 策略二交易记录 */}
      <Card
        size="small"
        title={<Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>策略二 · 历史交易记录</Text>}
        style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={strategy2Trades}
          columns={tradeColumns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: "transparent" }}
        />
      </Card>
    </div>
  );
};

export default StrategyPerfPage;
