import { Card, Tag, List } from "antd";
import {
  RiseOutlined,
  FallOutlined,
  ClusterOutlined,
  ExperimentOutlined,
  BulbOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

interface CandidateItem {
  name: string;
  code: string;
  score: number;
  strategy: string;
  changePct: number;
}

const CANDIDATES: CandidateItem[] = [
  { name: "宁德时代", code: "300750", score: 87, strategy: "策略一", changePct: 3.25 },
  { name: "比亚迪", code: "002594", score: 82, strategy: "策略二", changePct: -1.48 },
  { name: "中科曙光", code: "603019", score: 78, strategy: "策略一", changePct: 5.62 },
  { name: "北方华创", code: "002371", score: 74, strategy: "策略二", changePct: -0.93 },
  { name: "金山办公", code: "688111", score: 71, strategy: "策略一", changePct: 2.17 },
];

function MobileStockPool() {
  const countTotal = CANDIDATES.length;
  const countS1 = CANDIDATES.filter((c) => c.strategy === "策略一").length;
  const countS2 = CANDIDATES.filter((c) => c.strategy === "策略二").length;

  return (
    <div style={{ paddingBottom: 16 }}>
      {/* Header */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: colors.text,
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <ClusterOutlined style={{ color: colors.nebula }} />
        股票池
      </div>

      {/* Stats Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <Card
          size="small"
          style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 10,
          }}
          bodyStyle={{ padding: "10px", textAlign: "center" }}
        >
          <div style={{ color: colors.muted, fontSize: 11 }}>候选总数</div>
          <div style={{ color: colors.shard, fontSize: 22, fontWeight: 700 }}>
            {countTotal}
          </div>
        </Card>
        <Card
          size="small"
          style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 10,
          }}
          bodyStyle={{ padding: "10px", textAlign: "center" }}
        >
          <div style={{ color: colors.muted, fontSize: 11 }}>
            <ExperimentOutlined style={{ marginRight: 3 }} />
            策略一
          </div>
          <div style={{ color: colors.nebula, fontSize: 22, fontWeight: 700 }}>
            {countS1}
          </div>
        </Card>
        <Card
          size="small"
          style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 10,
          }}
          bodyStyle={{ padding: "10px", textAlign: "center" }}
        >
          <div style={{ color: colors.muted, fontSize: 11 }}>
            <BulbOutlined style={{ marginRight: 3 }} />
            策略二
          </div>
          <div style={{ color: colors.amber, fontSize: 22, fontWeight: 700 }}>
            {countS2}
          </div>
        </Card>
      </div>

      {/* Candidate List */}
      <List
        dataSource={CANDIDATES}
        split={false}
        renderItem={(item) => {
          const isUp = item.changePct >= 0;
          return (
            <List.Item
              style={{
                background: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 10,
                marginBottom: 6,
                padding: "10px 12px",
                display: "block",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      color: colors.text,
                      fontSize: 14,
                      fontWeight: 600,
                    }}
                  >
                    {item.name}
                    <span style={{ color: colors.dimmed, fontSize: 11, marginLeft: 6 }}>
                      {item.code}
                    </span>
                  </div>
                  <div style={{ marginTop: 4, display: "flex", gap: 6, alignItems: "center" }}>
                    <Tag
                      color={colors.nebula}
                      style={{
                        fontSize: 11,
                        borderRadius: 8,
                        padding: "0 6px",
                        lineHeight: "18px",
                        fontWeight: 700,
                        color: "#fff",
                      }}
                    >
                      {item.score}分
                    </Tag>
                    <Tag
                      style={{
                        fontSize: 10,
                        borderRadius: 8,
                        padding: "0 6px",
                        lineHeight: "18px",
                        border: `1px solid ${colors.border}`,
                        background: "transparent",
                        color: colors.muted,
                      }}
                    >
                      {item.strategy}
                    </Tag>
                  </div>
                </div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: isUp ? colors.gold : colors.danger,
                    whiteSpace: "nowrap",
                  }}
                >
                  {isUp ? (
                    <RiseOutlined style={{ fontSize: 12, marginRight: 3 }} />
                  ) : (
                    <FallOutlined style={{ fontSize: 12, marginRight: 3 }} />
                  )}
                  {isUp ? "+" : ""}
                  {item.changePct.toFixed(2)}%
                </div>
              </div>
            </List.Item>
          );
        }}
      />
    </div>
  );
}

export default MobileStockPool;
