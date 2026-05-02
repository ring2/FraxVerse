import { useState } from "react";
import { Card, Tag, Input, Button, message } from "antd";
import {
  SwapOutlined,
  WalletOutlined,
  BankOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import type { TradeMode } from "../../types/trade";

interface PositionItem {
  name: string;
  code: string;
  volume: number;
  avgCost: number;
  currentPrice: number;
  pnlPct: number;
}

const POSITIONS: PositionItem[] = [
  { name: "宁德时代", code: "300750", volume: 200, avgCost: 185.50, currentPrice: 195.32, pnlPct: 5.32 },
  { name: "贵州茅台", code: "600519", volume: 100, avgCost: 1580.00, currentPrice: 1546.20, pnlPct: -2.15 },
  { name: "科大讯飞", code: "002230", volume: 500, avgCost: 42.30, currentPrice: 46.10, pnlPct: 8.77 },
];

function MobileTrade() {
  const [stockCode, setStockCode] = useState("");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [volume, setVolume] = useState("");
  const [tradeMode] = useState<TradeMode>("SIMULATION");

  const handleSubmit = () => {
    if (!stockCode.trim()) {
      message.warning("请输入股票代码");
      return;
    }
    if (!volume || parseInt(volume, 10) <= 0) {
      message.warning("请输入有效数量");
      return;
    }
    message.success(
      `下单成功: ${direction === "buy" ? "买入" : "卖出"} ${stockCode} ${volume}股`
    );
    setStockCode("");
    setVolume("");
  };

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
        <SwapOutlined style={{ color: colors.nebula }} />
        交易
        <Tag
          color={
            tradeMode === "LIVE"
              ? colors.danger
              : tradeMode === "PAPER"
              ? colors.amber
              : colors.shard
          }
          style={{ marginLeft: "auto", fontSize: 10, borderRadius: 12 }}
        >
          {tradeMode}
        </Tag>
      </div>

      {/* Current Positions */}
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
        <WalletOutlined style={{ color: colors.gold }} />
        当前持仓
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
            bodyStyle={{ padding: "10px 12px" }}
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
                  <span style={{ color: colors.dimmed, fontSize: 11, marginLeft: 6 }}>
                    {pos.code}
                  </span>
                </div>
                <div style={{ color: colors.dimmed, fontSize: 11, marginTop: 2 }}>
                  {pos.volume}股 · 成本{pos.avgCost.toFixed(2)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: colors.muted, fontSize: 11 }}>
                  现价 {pos.currentPrice.toFixed(2)}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: isProfit ? colors.gold : colors.danger,
                  }}
                >
                  {isProfit ? "+" : ""}
                  {pos.pnlPct.toFixed(2)}%
                </div>
              </div>
            </div>
          </Card>
        );
      })}

      {/* Quick Order Form */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          margin: "12px 0 8px",
          color: colors.muted,
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        <BankOutlined style={{ color: colors.shard }} />
        快速下单
      </div>

      <Card
        size="small"
        style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
        }}
        bodyStyle={{ padding: 14 }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Stock Code */}
          <Input
            placeholder="股票代码"
            value={stockCode}
            onChange={(e) => setStockCode(e.target.value.toUpperCase())}
            style={{
              background: colors.surface,
              border: `1px solid ${colors.border}`,
              color: colors.text,
              borderRadius: 8,
            }}
          />

          {/* Direction Toggle */}
          <div style={{ display: "flex", gap: 8 }}>
            <Button
              size="small"
              type={direction === "buy" ? "primary" : "default"}
              onClick={() => setDirection("buy")}
              style={{
                flex: 1,
                borderRadius: 8,
                background: direction === "buy" ? colors.success : "transparent",
                borderColor: direction === "buy" ? colors.success : colors.border,
                color: direction === "buy" ? "#fff" : colors.muted,
                fontWeight: 600,
              }}
            >
              买入
            </Button>
            <Button
              size="small"
              type={direction === "sell" ? "primary" : "default"}
              onClick={() => setDirection("sell")}
              style={{
                flex: 1,
                borderRadius: 8,
                background: direction === "sell" ? colors.danger : "transparent",
                borderColor: direction === "sell" ? colors.danger : colors.border,
                color: direction === "sell" ? "#fff" : colors.muted,
                fontWeight: 600,
              }}
            >
              卖出
            </Button>
          </div>

          {/* Volume */}
          <Input
            placeholder="数量（股）"
            type="number"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            style={{
              background: colors.surface,
              border: `1px solid ${colors.border}`,
              color: colors.text,
              borderRadius: 8,
            }}
          />

          {/* Confirm Button */}
          <Button
            type="primary"
            size="large"
            onClick={handleSubmit}
            style={{
              borderRadius: 8,
              height: 42,
              fontWeight: 700,
              fontSize: 15,
              background: colors.gradients.primary,
              border: "none",
            }}
          >
            确认下单
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default MobileTrade;
