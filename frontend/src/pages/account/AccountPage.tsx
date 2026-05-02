import { useState, useMemo, useEffect, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  DatePicker,
  Table,
  Space,
  Empty,
  App,
} from 'antd';
import ReactECharts from 'echarts-for-react';
import { colors } from '../../theme/colors';
import type { PortfolioSummary, PositionItem } from '../../types/api-extended';
import { portfolioService } from '../../services/portfolioService';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ─── Helpers ──────────────────────────────────────────────────

function formatMoney(v: number | string): string {
  const num = typeof v === 'string' ? parseFloat(v) : v;
  return `¥ ${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function valColor(v: number): string {
  if (v > 0) return colors.gold;
  if (v < 0) return colors.danger;
  return colors.text;
}

function signPrefix(v: number): string {
  return v > 0 ? '+' : '';
}

/** Parse a backend decimal string to a number, defaulting to 0. */
function toNum(v: string | number | null | undefined): number {
  if (v == null) return 0;
  if (typeof v === 'number') return v;
  const n = parseFloat(v);
  return Number.isNaN(n) ? 0 : n;
}

// ─── Component ────────────────────────────────────────────────

const AccountPage: React.FC = () => {
  const { message } = App.useApp();

  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  // ── data fetching ──
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, posData] = await Promise.all([
        portfolioService.getSummary(),
        portfolioService.getPositions(),
      ]);
      setSummary(summaryData);
      setPositions(posData);
    } catch (e) {
      console.error('AccountPage: failed to load data', e);
      message.error('加载账户数据失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── derived display values ──
  const display = useMemo(() => {
    const s = summary;
    return {
      totalAssets: toNum(s?.total_asset),
      availableCash: toNum(s?.available_cash),
      marketValue: toNum(s?.total_asset) - toNum(s?.available_cash),
      dailyPnl: toNum(s?.daily_pnl),
      unrealizedPnl: toNum(s?.unrealized_pnl),
      totalPositionPct: toNum(s?.total_position_pct),
      positionCount: s?.position_count ?? 0,
    };
  }, [summary]);

  // ── NAV curve (generated from summary data or static placeholders) ──
  const navData = useMemo(() => {
    const dates: string[] = [];
    const values: number[] = [];
    const start = dayjs('2026-01-02');
    const end = dayjs('2026-04-30');
    let nav = 1.0;
    const totalDays = end.diff(start, 'day') + 1;
    const targetNav = display.unrealizedPnl > 0 ? 1 + display.unrealizedPnl / 1000000 : 1.05;

    for (let i = 0; i < totalDays; i++) {
      const d = start.add(i, 'day');
      if (d.day() === 0 || d.day() === 6) continue;
      dates.push(d.format('YYYY-MM-DD'));
      const drift = (targetNav - 1.0) / Math.max(totalDays / 2, 1);
      const noise = (Math.random() - 0.5) * 0.006;
      nav = Math.max(0.9, nav + drift + noise);
      values.push(parseFloat(nav.toFixed(5)));
    }
    return { dates, values };
  }, [display.unrealizedPnl]);

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
      key: 'stockName',
      render: (_: string, record: PositionItem) => (
        <Space size={4}>
          <Text style={{ color: colors.text, fontWeight: 500 }}>{record.stock_name ?? record.stock_code}</Text>
          <Text style={{ color: colors.dimmed, fontSize: 12 }}>{record.stock_code}</Text>
        </Space>
      ),
    },
    {
      title: '数量',
      dataIndex: 'total_volume',
      key: 'total_volume',
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.text }}>{v.toLocaleString()}</Text>
      ),
    },
    {
      title: '成本',
      dataIndex: 'cost_price',
      key: 'cost_price',
      align: 'right' as const,
      render: (v: string) => (
        <Text style={{ color: colors.text }}>{`¥ ${toNum(v).toFixed(2)}`}</Text>
      ),
    },
    {
      title: '市值',
      dataIndex: 'market_value',
      key: 'market_value',
      align: 'right' as const,
      render: (v: string) => (
        <Text style={{ color: colors.text }}>{formatMoney(v)}</Text>
      ),
    },
    {
      title: '盈亏',
      dataIndex: 'unrealized_pnl',
      key: 'unrealized_pnl',
      align: 'right' as const,
      render: (v: string) => {
        const num = toNum(v);
        return (
          <Text style={{ color: valColor(num), fontWeight: 600 }}>
            {signPrefix(num)}{formatMoney(v)}
          </Text>
        );
      },
    },
    {
      title: '盈亏%',
      dataIndex: 'unrealized_pnl_pct',
      key: 'unrealized_pnl_pct',
      align: 'right' as const,
      render: (v: string) => {
        const num = toNum(v);
        return (
          <Text style={{ color: valColor(num), fontWeight: 600 }}>
            {signPrefix(num)}{num.toFixed(2)}%
          </Text>
        );
      },
    },
    {
      title: '占比',
      dataIndex: 'position_pct',
      key: 'position_pct',
      align: 'right' as const,
      render: (v: string) => {
        const num = toNum(v);
        return (
          <Text style={{ color: colors.text }}>
            {num.toFixed(2)}%
          </Text>
        );
      },
    },
    {
      title: '建仓日',
      dataIndex: 'entry_date',
      key: 'entry_date',
      align: 'center' as const,
      render: (v: string | null) => (
        <Text style={{ color: colors.dimmed, fontSize: 12 }}>
          {v ?? '—'}
        </Text>
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
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总资产</span>}
              value={formatMoney(display.totalAssets)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>可用资金</span>}
              value={formatMoney(display.availableCash)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>持仓市值</span>}
              value={formatMoney(display.marketValue)}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>今日盈亏</span>}
              value={`${signPrefix(display.dailyPnl)}${formatMoney(display.dailyPnl)}`}
              valueStyle={{ color: valColor(display.dailyPnl), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>浮动盈亏</span>}
              value={`${signPrefix(display.unrealizedPnl)}${formatMoney(display.unrealizedPnl)}`}
              valueStyle={{ color: valColor(display.unrealizedPnl), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>仓位</span>}
              value={`${display.totalPositionPct.toFixed(2)}%`}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>持仓数量</span>}
              value={display.positionCount}
              valueStyle={{ color: colors.text, fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6} lg={3}>
          <Card
            size="small"
            loading={loading}
            styles={{ body: { padding: 16 } }}
            style={{ background: colors.card, borderColor: colors.border, borderRadius: 8 }}
          >
            <Statistic
              title={<span style={{ color: colors.muted, fontSize: 12 }}>总收益</span>}
              value={
                display.unrealizedPnl > 0
                  ? `+${((display.unrealizedPnl / (display.totalAssets - display.unrealizedPnl)) * 100 || 0).toFixed(2)}%`
                  : `${((display.unrealizedPnl / (display.totalAssets - display.unrealizedPnl)) * 100 || 0).toFixed(2)}%`
              }
              valueStyle={{ color: valColor(display.unrealizedPnl), fontSize: 16, fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* ══════ Row 2: NAV curve ══════ */}
      <Card
        size="small"
        loading={loading}
        style={{
          marginTop: 16,
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: '12px 16px' } }}
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
        loading={loading}
        style={{
          marginTop: 16,
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={positions}
          columns={columns}
          rowKey="stock_code"
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
