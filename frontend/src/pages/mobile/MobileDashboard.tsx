import { useEffect, useState } from "react";
import { Card, Statistic, Tag, Row, Col, Spin, App } from "antd";
import {
  FundOutlined,
  StockOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";
import { marketService } from "../../services/marketService";
import type {
  PortfolioSummary,
  TradeModeResponse,
  MarketStateResponse,
} from "../../types/api-extended";

function MobileDashboard() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [tradeMode, setTradeMode] = useState<TradeModeResponse | null>(null);
  const [marketState, setMarketState] = useState<MarketStateResponse | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      portfolioService.getSummary(),
      tradeService.getMode(),
      marketService.getMarketState(),
    ])
      .then(([s, m, ms]) => {
        if (cancelled) return;
        setSummary(s);
        setTradeMode(m);
        setMarketState(ms);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load dashboard data:", err);
        message.error("加载仪表盘数据失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const getMarketTag = (): { label: string; color: string } => {
    if (!marketState) return { label: "⏳ 加载中", color: colors.muted };
    const state = marketState.current_state;
    if (state === "bull") return { label: "🐂 牛市", color: colors.success };
    if (state === "bear") return { label: "🐻 熊市", color: colors.danger };
    return { label: "⚖️ 震荡", color: colors.amber };
  };

  const marketTag = getMarketTag();
  const mode = tradeMode?.current_mode ?? "SIMULATION";

  const modeTagColor =
    mode === "LIVE"
      ? colors.danger
      : mode === "PAPER"
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
        <FundOutlined style={{ color: colors.nebula }} />
        看盘
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          <Tag
            color={modeTagColor}
            style={{ fontSize: 10, borderRadius: 12, marginRight: 4 }}
          >
            {mode}
          </Tag>
          <Tag
            color={marketTag.color}
            style={{ fontSize: 11, borderRadius: 12 }}
          >
            {marketTag.label}
          </Tag>
        </div>
      </div>

      {/* Summary Cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col span={8}>
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
                <span style={{ color: colors.muted, fontSize: 11 }}>
                  总资产
                </span>
              }
              value={summary?.total_asset != null ? `¥${Number(summary.total_asset).toLocaleString()}` : "--"}
              valueStyle={{
                fontSize: 14,
                fontWeight: 600,
                color: colors.text,
                lineHeight: 1.4,
              }}
            />
          </Card>
        </Col>
        <Col span={8}>
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
                <span style={{ color: colors.muted, fontSize: 11 }}>
                  持仓数
                </span>
              }
              value={summary?.position_count ?? 0}
              valueStyle={{
                fontSize: 14,
                fontWeight: 600,
                color: colors.text,
                lineHeight: 1.4,
              }}
            />
          </Card>
        </Col>
        <Col span={8}>
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
                <span style={{ color: colors.muted, fontSize: 11 }}>
                  日盈亏
                </span>
              }
              value={summary?.daily_pnl != null ? `¥${Number(summary.daily_pnl).toLocaleString()}` : "--"}
              valueStyle={{
                fontSize: 14,
                fontWeight: 600,
                color: colors.text,
                lineHeight: 1.4,
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Market State Info */}
      {marketState && (
        <Card
          size="small"
          style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 10,
            marginBottom: 12,
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
              <div style={{ color: colors.muted, fontSize: 11 }}>市场状态</div>
              <div style={{ color: colors.text, fontSize: 14, fontWeight: 600 }}>
                {marketState.current_state === "bull"
                  ? "🐂 牛市"
                  : marketState.current_state === "bear"
                  ? "🐻 熊市"
                  : "⚖️ 震荡"}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: colors.muted, fontSize: 11 }}>
                主线板块
              </div>
              <div style={{ color: colors.text, fontSize: 13 }}>
                {marketState.main_line_sector ?? "无"}
              </div>
            </div>
          </div>
        </Card>
      )}

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

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 12px",
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
        }}
      >
        <div>
          <div style={{ color: colors.text, fontSize: 14, fontWeight: 600 }}>
            可用资金
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: colors.text,
            }}
          >
            {summary?.available_cash != null ? `¥${Number(summary.available_cash).toLocaleString()}` : "--"}
          </div>
          <div style={{ color: colors.dimmed, fontSize: 11 }}>
            仓位 {summary?.total_position_pct ?? "--"}%
          </div>
        </div>
      </div>
    </div>
  );
}

export default MobileDashboard;
