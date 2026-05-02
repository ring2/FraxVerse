import { useMemo, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, DatePicker, Table, Tag, Space, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import { colors } from '../../theme/colors';
import type { PositionItem } from '../../types/trade';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ─── Mock Data ────────────────────────────────────────────────

const mockAccount = {
  totalAssets: 1286532,
  availableCash: 652831,
  marketValue: 633701,
  todayPnl: 12568,
  totalReturnPct: 28.65,
  annualReturnPct: 15.32,
  maxDrawdownPct: -8.43,
  sharpeRatio: 1.26,
};

function generateNavData(): { dates: string[]; values: number[] } {
  const dates: string[] = [];
  const values: number[] = [];
  const start = dayjs('2026-01-02');
  const end = dayjs('2026-04-30');
  let nav = 1.0;
  const totalDays = end.diff(start, 'day') + 1;
  const targetNav = 1.2865;

  for (let i = 0; i < totalDays; i++) {
    const d = start.add(i, 'day');
    // Skip weekends
    if (d.day() === 0 || d.day() === 6) continue;
    dates.push(d.format('YYYY-MM-DD'));

    // Smooth random walk toward target
    const drift = (targetNav - 1.0) / 80;
    const noise = (Math.random() - 0.5) * 0.006;
    nav = Math.max(0.9, nav + drift + noise);
    values.push(parseFloat(nav.toFixed(5)));
  }
  return { dates, values };
}

const mockPositions: (PositionItem & { marketValue: number })[] = [
  {
    id: '1',
    stockCode: '600519',
    stockName: '贵州茅台',
    volume: 1200,
    avgCost: 185.5,
    currentPrice: 198.6,
    marketValue: 238320,
    pnl: 15720,
    pnlPct: 7.06,
    strategy: '价值投资',
    openedAt: '2025-06-15',
  },
  {
    id: '2',
    stockCode: '300750',
    stockName: '宁德时代',
    volume: 3500,
    avgCost: 68.2,
    currentPrice: 72.15,
    marketValue: 252525,
    pnl: 13825,
    pnlPct: 5.79,
    strategy: '趋势跟踪',
    openedAt: '2025-08-20',
  },
  {
    id: '3',
    stockCode: '601318',
    stockName: '中国平安',
    volume: 2800,
    avgCost: 52.8,
    currentPrice: 51.02,
    marketValue: 142856,
    pnl: -4984,
    pnlPct: -3.37,
    strategy: '网格交易',
    openedAt: '2025-10-01',
  },
];

// ─── Helpers ──────────────────────────────────────────────────

function formatMoney(v: number): string {
  return `¥ ${v.toLocaleString('zh-CN')}`;
}

function valColor(v: number): string {
  if (v > 0) return colors.gold;
  if (v < 0) return colors.danger;
  return colors.text;
}

function signPrefix(v: number): string {
  return v > 0 ? '+' : '';
}

// ─── Component ────────────────────────────────────────────────

const AccountPage: React.FC = () => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const navData = useMemo(() => generateNavData(), []);

  // Filter nav data by selected date range
  const filteredNav = useMemo(() => {
    if (!dateRange || !dateRange[0] || !dateRange[1]) return navData;
    const [start, end] = dateRange;
    const startStr = start.format('YYYY-MM-DD');
    const endStr = end.format('YYYY-MM-DD');
    const idxStart = navData.dates.findIndex((d) => d >= startStr);
    const idxEnd = navData.dates.findLastIndex((d) => d <= endStr);
    if (idxStart === -1 || idxEnd === -1) return navData;
    return {
      dates: navData.dates.slice(idxStart, idxEnd + 1),
      values: navData.values.slice(idxStart, idxEnd + 1),
    };
  }, [dateRange, navData]);

  const chartOption = useMemo(
    () => ({
      backgroundColor: 'transparent',
      grid: { left: 48, right: 16, top: 24, bottom: 60 },
      xAxis: {
        type: 'category' as const,
        data: filteredNav.dates,
        axisLine: { lineStyle: { color: colors.border } },
        axisLabel: {
          color: colors.muted,
          fontSize: 11,
          formatter: (v: string) => dayjs(v).format('MM/DD'),
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value' as const,
        scale: true,
        splitLine: { lineStyle: { color: colors.border, type: 'dashed' as const } },
        axisLabel: { color: colors.muted, fontSize: 11 },
      },
      series: [
        {
          type: 'line' as const,
          data: filteredNav.values,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: colors.nebula, width: 2 },
          areaStyle: {
            color: {
              type: 'linear' as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(107, 92, 231, 0.45)' },
                { offset: 1, color: 'rgba(107, 92, 231, 0.02)' },
              ],
            },
          },
        },
      ],
      dataZoom: [
        {
          type: 'inside' as const,
          start: 0,
          end: 100,
        },
        {
          type: 'slider' as const,
          start: 0,
          end: 100,
          height: 20,
          bottom: 8,
          borderColor: colors.border,
          fillerColor: 'rgba(107, 92, 231, 0.25)',
          handleStyle: { color: colors.nebula },
          textStyle: { color: colors.muted, fontSize: 10 },
        },
      ],
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: colors.surface,
        borderColor: colors.border,
        textStyle: { color: colors.text, fontSize: 12 },
        formatter: (params: { value: number }[]) => {
          if (!params || !params[0]) return '';
          return `净值: ${params[0].value.toFixed(4)}`;
        },
      },
    }),
    [filteredNav],
  );

  // ── Table columns ──
  const columns = [
    {
      title: '标的',
      dataIndex: 'stockName',
      key: 'stockName',
      render: (_: string, record: PositionItem) => (
        <Space size={4}>
          <Text style={{ color: colors.text, fontWeight: 500 }}>{record.stockName}</Text>
          <Text style={{ color: colors.dimmed, fontSize: 12 }}>{record.stockCode}</Text>
        </Space>
      ),
    },
    {
      title: '数量',
      dataIndex: 'volume',
      key: 'volume',
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.text }}>{v.toLocaleString()}</Text>
      ),
    },
    {
      title: '成本',
      dataIndex: 'avgCost',
      key: 'avgCost',
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.text }}>{`¥ ${v.toFixed(2)}`}</Text>
      ),
    },
    {
      title: '现价',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.text }}>{`¥ ${v.toFixed(2)}`}</Text>
      ),
    },
    {
      title: '盈亏%',
      dataIndex: 'pnlPct',
      key: 'pnlPct',
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: valColor(v), fontWeight: 600 }}>
          {signPrefix(v)}{v.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
      align: 'center' as const,
      render: (v: string) => (
        <Tag color="purple" style={{ borderRadius: 4, margin: 0 }}>
          {v}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: '16px 0' }}>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        资产星盘
      </Title>

      {/* ══════ Row 1: Stat cards ══════ */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总资产</span>}
              value={formatMoney(mockAccount.totalAssets)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>可用资金</span>}
              value={formatMoney(mockAccount.availableCash)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>持仓市值</span>}
              value={formatMoney(mockAccount.marketValue)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>今日盈亏</span>}
              value={`${signPrefix(mockAccount.todayPnl)}${formatMoney(mockAccount.todayPnl)}`}
              valueStyle={{ color: valColor(mockAccount.todayPnl), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总收益</span>}
              value={`${signPrefix(mockAccount.totalReturnPct)}${mockAccount.totalReturnPct.toFixed(2)}%`}
              valueStyle={{ color: valColor(mockAccount.totalReturnPct), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>年化收益</span>}
              value={`${signPrefix(mockAccount.annualReturnPct)}${mockAccount.annualReturnPct.toFixed(2)}%`}
              valueStyle={{ color: valColor(mockAccount.annualReturnPct), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>最大回撤</span>}
              value={`${mockAccount.maxDrawdownPct.toFixed(2)}%`}
              valueStyle={{ color: colors.success, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>夏普比率</span>}
              value={mockAccount.sharpeRatio.toFixed(2)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* ══════ Row 2: NAV curve ══════ */}
      <Card
        size="small"
        style={{
          marginTop: 16,
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        <Row justify="space-between" align="middle" style={{ marginBottom: 8 }}>
          <Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>
            净值曲线
          </Text>
          <RangePicker
            size="small"
            allowClear
            onChange={(dates) =>
              setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)
            }
            style={{ background: colors.surface, borderColor: colors.border, color: colors.text }}
          />
        </Row>
        <ReactECharts option={chartOption} style={{ height: 320 }} notMerge />
      </Card>

      {/* ══════ Row 3: Positions table ══════ */}
      <Card
        size="small"
        title={
          <Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>
            当前持仓概览
          </Text>
        }
        style={{
          marginTop: 16,
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        bodyStyle={{ padding: 0 }}
      >
        <Table
          dataSource={mockPositions}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: 'transparent' }}
          locale={{
            emptyText: <Empty description="暂无持仓" />,
          }}
        />
      </Card>
    </div>
  );
};

export default AccountPage;
