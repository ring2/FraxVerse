import { useState, useMemo } from "react";
import { Table, Tag, Select, Input, Typography } from "antd";
import {
  SearchOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type StrategyType = "量价突破" | "资金共振";
type ConfirmStatus = "待确认" | "已确认" | "已过期";

interface StockCandidate {
  code: string;
  name: string;
  compositeScore: number; // 综合评分 0‑100
  priceVolume: number;    // 量价评分
  fundFlow: number;       // 资金评分
  sentiment: number;      // 情绪评分
  dominantForce: number;  // 主力评分
  logicScore: number;     // 逻辑评分
  strategy: StrategyType;
  changePct: number;      // 涨跌幅（%）
  status: ConfirmStatus;
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockData: StockCandidate[] = [
  {
    code: "600519",
    name: "贵州茅台",
    compositeScore: 85,
    priceVolume: 82,
    fundFlow: 88,
    sentiment: 79,
    dominantForce: 90,
    logicScore: 86,
    strategy: "量价突破",
    changePct: 2.35,
    status: "待确认",
  },
  {
    code: "000858",
    name: "五粮液",
    compositeScore: 72,
    priceVolume: 75,
    fundFlow: 68,
    sentiment: 70,
    dominantForce: 74,
    logicScore: 73,
    strategy: "量价突破",
    changePct: -1.28,
    status: "已确认",
  },
  {
    code: "002415",
    name: "海康威视",
    compositeScore: 91,
    priceVolume: 93,
    fundFlow: 89,
    sentiment: 88,
    dominantForce: 94,
    logicScore: 91,
    strategy: "资金共振",
    changePct: 4.56,
    status: "待确认",
  },
  {
    code: "300750",
    name: "宁德时代",
    compositeScore: 63,
    priceVolume: 60,
    fundFlow: 65,
    sentiment: 58,
    dominantForce: 67,
    logicScore: 65,
    strategy: "资金共振",
    changePct: -3.42,
    status: "已过期",
  },
  {
    code: "601318",
    name: "中国平安",
    compositeScore: 78,
    priceVolume: 80,
    fundFlow: 75,
    sentiment: 76,
    dominantForce: 79,
    logicScore: 80,
    strategy: "量价突破",
    changePct: 0.87,
    status: "已确认",
  },
  {
    code: "002230",
    name: "科大讯飞",
    compositeScore: 88,
    priceVolume: 86,
    fundFlow: 90,
    sentiment: 92,
    dominantForce: 85,
    logicScore: 87,
    strategy: "资金共振",
    changePct: 5.12,
    status: "待确认",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const strategyOptions = [
  { value: "", label: "全部策略" },
  { value: "量价突破", label: "策略一 · 量价突破" },
  { value: "资金共振", label: "策略二 · 资金共振" },
];

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "待确认", label: "待确认" },
  { value: "已确认", label: "已确认" },
  { value: "已过期", label: "已过期" },
];

const statusColorMap: Record<ConfirmStatus, string> = {
  "待确认": colors.gold,
  "已确认": colors.success,
  "已过期": colors.danger,
};

const strategyColorMap: Record<StrategyType, string> = {
  "量价突破": colors.nebula,
  "资金共振": colors.shard,
};

/** Format a score cell — purple bold for composite, normal for the rest. */
const ScoreCell: React.FC<{
  value: number;
  composite?: boolean;
}> = ({ value, composite }) => (
  <span
    style={{
      color: composite ? colors.nebula : colors.text,
      fontWeight: composite ? 700 : 400,
      fontFamily: "monospace",
    }}
  >
    {value}
  </span>
);

/** Colour-coded change cell. */
const ChangeCell: React.FC<{ value: number }> = ({ value }) => {
  const color = value > 0 ? colors.danger : value < 0 ? colors.success : colors.muted;
  const prefix = value > 0 ? "+" : "";
  return (
    <span style={{ color, fontWeight: 600, fontFamily: "monospace" }}>
      {prefix}
      {value.toFixed(2)}%
    </span>
  );
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const StockPoolPage: React.FC = () => {
  const [strategy, setStrategy] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [searchText, setSearchText] = useState<string>("");

  // ---- Derived filtered data ----
  const filteredData = useMemo(() => {
    return mockData.filter((item) => {
      if (strategy && item.strategy !== strategy) return false;
      if (status && item.status !== status) return false;
      if (searchText) {
        const q = searchText.toLowerCase();
        if (
          !item.code.toLowerCase().includes(q) &&
          !item.name.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [strategy, status, searchText]);

  // ---- Ant Design columns ----
  const columns = [
    {
      title: "排名",
      key: "rank",
      width: 60,
      render: (_: unknown, __: unknown, index: number) => (
        <span style={{ color: colors.muted, fontFamily: "monospace" }}>
          {index + 1}
        </span>
      ),
    },
    {
      title: "代码",
      dataIndex: "code",
      key: "code",
      width: 100,
      render: (val: string) => (
        <span style={{ color: colors.shard, fontFamily: "monospace" }}>
          {val}
        </span>
      ),
    },
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 110,
      render: (val: string) => (
        <span style={{ color: colors.text }}>{val}</span>
      ),
    },
    {
      title: "综合评分",
      dataIndex: "compositeScore",
      key: "compositeScore",
      width: 100,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.compositeScore - b.compositeScore,
      render: (val: number) => <ScoreCell value={val} composite />,
    },
    {
      title: "量价",
      dataIndex: "priceVolume",
      key: "priceVolume",
      width: 70,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.priceVolume - b.priceVolume,
      render: (val: number) => <ScoreCell value={val} />,
    },
    {
      title: "资金",
      dataIndex: "fundFlow",
      key: "fundFlow",
      width: 70,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.fundFlow - b.fundFlow,
      render: (val: number) => <ScoreCell value={val} />,
    },
    {
      title: "情绪",
      dataIndex: "sentiment",
      key: "sentiment",
      width: 70,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.sentiment - b.sentiment,
      render: (val: number) => <ScoreCell value={val} />,
    },
    {
      title: "主力",
      dataIndex: "dominantForce",
      key: "dominantForce",
      width: 70,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.dominantForce - b.dominantForce,
      render: (val: number) => <ScoreCell value={val} />,
    },
    {
      title: "逻辑",
      dataIndex: "logicScore",
      key: "logicScore",
      width: 70,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.logicScore - b.logicScore,
      render: (val: number) => <ScoreCell value={val} />,
    },
    {
      title: "策略标签",
      dataIndex: "strategy",
      key: "strategy",
      width: 130,
      render: (val: StrategyType) => (
        <Tag color={strategyColorMap[val]} style={{ borderRadius: 4 }}>
          {val}
        </Tag>
      ),
    },
    {
      title: "涨跌幅",
      dataIndex: "changePct",
      key: "changePct",
      width: 90,
      sorter: (a: StockCandidate, b: StockCandidate) =>
        a.changePct - b.changePct,
      render: (val: number) => <ChangeCell value={val} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (val: ConfirmStatus) => (
        <Tag
          color={statusColorMap[val]}
          style={{
            borderRadius: 4,
            color: "#fff",
            border: "none",
          }}
        >
          {val}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <Title level={3} style={{ color: colors.text, marginBottom: 4 }}>
        碎片候选
      </Title>
      <Text style={{ color: colors.muted, display: "block", marginBottom: 24 }}>
        待聚之光
      </Text>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 16,
          alignItems: "center",
        }}
      >
        <FilterOutlined style={{ color: colors.muted, fontSize: 16 }} />

        <Select
          value={strategy}
          onChange={setStrategy}
          options={strategyOptions}
          style={{ width: 180 }}
          popupMatchSelectWidth={false}
          variant="borderless"
          dropdownStyle={{
            background: colors.surface,
            border: `1px solid ${colors.border}`,
          }}
        />

        <Select
          value={status}
          onChange={setStatus}
          options={statusOptions}
          style={{ width: 130 }}
          popupMatchSelectWidth={false}
          variant="borderless"
          dropdownStyle={{
            background: colors.surface,
            border: `1px solid ${colors.border}`,
          }}
        />

        <Input
          prefix={<SearchOutlined style={{ color: colors.muted }} />}
          placeholder="搜索代码 / 名称"
          allowClear
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          variant="borderless"
          style={{
            width: 220,
            background: colors.card,
            color: colors.text,
            borderRadius: 6,
          }}
        />
      </div>

      {/* Table */}
      <div style={{ background: colors.card, borderRadius: 8, overflow: "hidden" }}>
        <Table
          dataSource={filteredData}
          columns={columns}
          rowKey="code"
          pagination={{
            pageSize: 15,
            showSizeChanger: false,
            showTotal: (total, range) => (
              <span style={{ color: colors.muted }}>
                {range[0]}-{range[1]} / 共 {total} 只
              </span>
            ),
          }}
          style={{ background: "transparent" }}
        />
      </div>
    </div>
  );
};

export default StockPoolPage;
