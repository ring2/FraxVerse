import { useEffect, useState } from "react";
import { Card, Tag, Input, Button, Spin, App } from "antd";
import {
  SwapOutlined,
  WalletOutlined,
  BankOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";
import type { PositionItem, OrderResponse, TradeModeResponse } from "../../types/api-extended";

function MobileTrade() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [tradeMode, setTradeMode] = useState<TradeModeResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [stockCode, setStockCode] = useState("");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [volume, setVolume] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      portfolioService.getPositions(),
      tradeService.getOrders(),
      tradeService.getMode(),
    ])
      .then(([p, o, m]) => {
        if (cancelled) return;
        setPositions(p);
        setOrders(o);
        setTradeMode(m);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load trade data:", err);
        message.error("加载交易数据失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const handleSubmit = async () => {
    if (!stockCode.trim()) {
      message.warning("请输入股票代码");
      return;
    }
    const vol = parseInt(volume, 10);
    if (!volume || vol <= 0) {
      message.warning("请输入有效数量");
      return;
    }

    setSubmitting(true);
    try {
      await tradeService.createOrder({
        stock_code: stockCode.trim().toUpperCase(),
        direction,
        order_type: "market",
        volume: vol,
      });
      message.success(
        `下单成功: ${direction === "buy" ? "买入" : "卖出"} ${stockCode} ${volume}股`
      );
      setStockCode("");
      setVolume("");
      // Refresh orders after placing
      const updatedOrders = await tradeService.getOrders();
      setOrders(updatedOrders);
    } catch (err: any) {
      console.error("Failed to place order:", err);
      message.error(err?.response?.data?.message || "下单失败");
    } finally {
      setSubmitting(false);
    }
  };

  const currentMode = tradeMode?.current_mode ?? "SIMULATION";
  const modeTagColor =
    currentMode === "LIVE"
      ? colors.danger
      : currentMode === "PAPER"
      ? colors.amber
      : colors.shard;

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 200,
        }}
      >
        <Spin tip="加载中..." />
      </div>
    );
  }

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
          color={modeTagColor}
          style={{ marginLeft: "auto", fontSize: 10, borderRadius: 12 }}
        >
          {currentMode}
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

      {positions.length === 0 && (
        <div
          style={{
            color: colors.dimmed,
            textAlign: "center",
            padding: "16px 0",
            fontSize: 13,
          }}
        >
          暂无持仓
        </div>
      )}

      {positions.map((pos) => {
        const pnlPct = parseFloat(pos.unrealized_pnl_pct);
        const isProfit = pnlPct >= 0;
        return (
          <Card
            key={pos.stock_code}
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
                  {pos.stock_name ?? pos.stock_code}
                  <span style={{ color: colors.dimmed, fontSize: 11, marginLeft: 6 }}>
                    {pos.stock_code}
                  </span>
                </div>
                <div style={{ color: colors.dimmed, fontSize: 11, marginTop: 2 }}>
                  {pos.total_volume}股 · 成本{pos.cost_price}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: colors.muted, fontSize: 11 }}>
                  市值 {pos.market_value}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: isProfit ? colors.gold : colors.danger,
                  }}
                >
                  {isProfit ? "+" : ""}
                  {pnlPct.toFixed(2)}%
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
        styles={{ body: { padding: 14 } }}
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
            loading={submitting}
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

      {/* Recent Orders */}
      {orders.length > 0 && (
        <>
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
            <SwapOutlined style={{ color: colors.nebula }} />
            最近订单
          </div>
          {orders.slice(0, 5).map((order) => (
            <Card
              key={order.id}
              size="small"
              style={{
                background: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 10,
                marginBottom: 6,
              }}
              styles={{ body: { padding: "8px 12px" } }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ color: colors.text, fontSize: 13, fontWeight: 600 }}>
                    {order.stock_code}
                    <span
                      style={{
                        color: colors.dimmed,
                        fontSize: 11,
                        marginLeft: 6,
                      }}
                    >
                      {order.direction === "buy" ? "买入" : "卖出"}
                    </span>
                  </div>
                  <div style={{ color: colors.dimmed, fontSize: 11 }}>
                    {order.volume}股 · {order.filled_volume}股已成交
                  </div>
                </div>
                <Tag
                  style={{
                    fontSize: 10,
                    borderRadius: 8,
                  }}
                  color={
                    order.status === "filled"
                      ? colors.success
                      : order.status === "pending"
                      ? colors.amber
                      : order.status === "canceled"
                      ? colors.danger
                      : colors.muted
                  }
                >
                  {order.status}
                </Tag>
              </div>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}

export default MobileTrade;
