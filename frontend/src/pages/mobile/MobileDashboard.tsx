import { Card, Statistic, Tag, Row, Col } from "antd";
import {
  CaretUpOutlined,
  CaretDownOutlined,
  FundOutlined,
  StockOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

interface MarketIndex {
  name: string;
  code: string;
  price: number;
  change: number;
  changePct: number;
}

interface Position {
  name: string;
  code: string;
  pnlPct: number;
  volume: number;
  strategy: string;
}

const MARKET_INDICES: MarketIndex[] = [
  { name: "上证指数", code: "000001", price: 3245.67, change: 12.34, changePct: 0.38 },
  { name: "深证成指", code: "399001", price: 10234.56, change: -45.12, changePct: -0.44 },
  { name: "创业板指", code: "399006", price: 2156.78, change: 23.45, changePct: 1.10 },
];

const POSITIONS: Position[] = [
  { name: "宁德时代", code: "300750", pnlPct: 5.32, volume: 200, strategy: "趋势跟踪" },
  { name: "贵州茅台", code: "600519", pnlPct: -2.15, volume: 100, strategy: "价值投资" },
  { name: "科大讯飞", code: "002230", pnlPct: 8.77, volume: 500, strategy: "动量策略" },
];

function getMarketStatusTag(): { label: string; color: string } {
  const sh = MARKET_INDICES[0].changePct;
  if (sh > 0.5) return { label: "🐂 牛市", color: colors.success };
  if (sh < -0.5) return { label: "🐻 熊市", color: colors.danger };
  return { label: "⚖️ 震荡", color: colors.amber };
}

function MobileDashboard() {
  const marketTag = getMarketStatusTag();

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
        <FundOutlined style={{ color: colors.nebula }} />
        看盘
        <Tag color={marketTag.color} style={{ marginLeft: "auto", fontSize: 11, borderRadius: 12 }}>
          {marketTag.label}
        </Tag>
      </div>

      {/* Market Index Cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        {MARKET_INDICES.map((idx) => {
          const isUp = idx.changePct >= 0;
          return (
            <Col span={8} key={idx.code}>
              <Card
                size="small"
                style={{
                  background: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 10,
                }}
                styles={{ body: { padding: "10px 8px" } }}
              >
                <Statistic
                  title={
                    <span style={{ color: colors.muted, fontSize: 11 }}>{idx.name}</span>
                  }
                  value={idx.price.toFixed(2)}
                  valueStyle={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: colors.text,
                    lineHeight: 1.4,
                  }}
                  suffix={
                    <span
                      style={{
                        fontSize: 11,
                        color: isUp ? colors.gold : colors.danger,
                        marginLeft: 4,
                      }}
                    >
                      {isUp ? (
                        <CaretUpOutlined style={{ fontSize: 10 }} />
                      ) : (
                        <CaretDownOutlined style={{ fontSize: 10 }} />
                      )}
                      {Math.abs(idx.changePct).toFixed(2)}%
                    </span>
                  }
                />
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Positions Section */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 8,
          color: colors.muted,
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        <StockOutlined style={{ color: colors.shard }} />
        持仓概览
      </div>

      {POSITIONS.map((pos) => {
        const isProfit = pos.pnlPct >= 0;
        return (
          <Card
            key={pos.code}
            size="small"
            style={{
              background: colors.card,
              border: `1px solid ${colors.border}`,
              borderRadius: 10,
              marginBottom: 6,
            }}
            styles={{ body: { padding: "10px 12px" } }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ color: colors.text, fontSize: 14, fontWeight: 600 }}>
                  {pos.name}
                </div>
                <div style={{ color: colors.dimmed, fontSize: 11 }}>{pos.code}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: isProfit ? colors.gold : colors.danger,
                  }}
                >
                  {isProfit ? "+" : ""}
                  {pos.pnlPct.toFixed(2)}%
                </div>
                <div style={{ color: colors.dimmed, fontSize: 11 }}>
                  {pos.volume}股 · {pos.strategy}
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export default MobileDashboard;
