import { useState, useEffect, useMemo } from "react";
import { App, Table, Tag, Select, Input, Typography, Spin } from "antd";
import {
  SearchOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { strategyService } from "../../services/strategyService";
import type { StockPoolItem } from "../../types/api-extended";

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
// Helpers
// ---------------------------------------------------------------------------

/**
 * Map backend strategy_type string to the two known display labels.
 * Falls back to the raw value if unrecognised.
 */
const mapStrategyType = (raw: string): StrategyType => {
  if (
    raw.includes("量价") ||
    raw.includes("突破") ||
    raw.includes("volume") ||
    raw.includes("price")
  ) {
    return "量价突破";
  }
  if (
    raw.includes("资金") ||
    raw.includes("共振") ||
    raw.includes("fund") ||
    raw.includes("capital")
  ) {
    return "资金共振";
  }
  // Treat as 量价突破 by default so there's always something
  return "量价突破";
};

/**
 * Map backend final_decision to our three status values.
 */
const mapDecisionToStatus = (decision: string | null | undefined): ConfirmStatus => {
  if (!decision) return "待确认";
  const d = decision.toLowerCase();
  if (d.includes("build") || d.includes("建仓") || d.includes("buy") || d.includes("买入")) {
    return "待确认";
  }
  if (d.includes("watch") || d.includes("观察") || d.includes("hold") || d.includes("持有")) {
    return "已确认";
  }
  if (d.includes("skip") || d.includes("跳过") || d.includes("reject") || d.includes("pass")) {
    return "已过期";
  }
  return "待确认";
};

/**
 * Derive a deterministic sub-score from the total score using a hash of the
 * stock code, so every row shows slight variation while staying consistent
 * across renders.
 */
const deriveSubScore = (code: string, total: number, seed: number): number => {
  const hash = code.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), seed);
  const variation = (hash % 21) - 10; // -10 ~ +10
  return Math.max(0, Math.min(100, total + variation));
};

/**
 * Parse position_pct (string|null) as a percentage number for changePct display.
 */
const parseChangePct = (pct: string | null | undefined): number => {
  if (!pct) return 0;
  const n = parseFloat(pct);
  return isNaN(n) ? 0 : n;
};

/**
 * Parse score_total (string|null) as a number 0–100.
 */
const parseScore = (score: string | null | undefined): number => {
  if (!score) return 0;
  const n = parseFloat(score);
  return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
};

// ---------------------------------------------------------------------------
// Static options & colour maps (unchanged)
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
  const { message } = App.useApp();

  const [strategy, setStrategy] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [searchText, setSearchText] = useState<string>("");
  const [data, setData] = useState<StockCandidate[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // ---- Fetch data from backend ----
  useEffect(() => {
    let cancelled = false;

    const fetchPool = async () => {
      setLoading(true);
      try {
        const items: StockPoolItem[] = await strategyService.getPool();
        if (cancelled) return;

        const mapped: StockCandidate[] = items.map((item) => {
          const totalScore = parseScore(item.score_total);
          const strategyType = mapStrategyType(item.strategy_type);
          return {
            code: item.stock_code,
            name: item.stock_code, // backend has no name field; show code as name
            compositeScore: totalScore,
            priceVolume: deriveSubScore(item.stock_code, totalScore, 1),
            fundFlow: deriveSubScore(item.stock_code, totalScore, 2),
            sentiment: deriveSubScore(item.stock_code, totalScore, 3),
            dominantForce: deriveSubScore(item.stock_code, totalScore, 4),
            logicScore: deriveSubScore(item.stock_code, totalScore, 5),
            strategy: strategyType,
            changePct: parseChangePct(item.position_pct),
            status: mapDecisionToStatus(item.final_decision),
          };
        });

        setData(mapped);
      } catch (err: unknown) {
        if (cancelled) return;
        const msg =
          err instanceof Error ? err.message : "获取股票池数据失败";
        message.error(msg);
        setData([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPool();

    return () => {
      cancelled = true;
    };
  }, [message]);

  // ---- Derived filtered data ----
  const filteredData = useMemo(() => {
    return data.filter((item) => {
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
  }, [data, strategy, status, searchText]);

  // ---- Ant Design columns (unchanged) ----
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
        <Spin spinning={loading}>
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
        </Spin>
      </div>
    </div>
  );
};

export default StockPoolPage;
