import { useEffect, useState } from "react";
import { Card, Tag, List, Spin, App } from "antd";
import {
  RiseOutlined,
  FallOutlined,
  ClusterOutlined,
  ExperimentOutlined,
  BulbOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { strategyService } from "../../services/strategyService";
import type { StockPoolItem } from "../../types/api-extended";

function MobileStockPool() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<StockPoolItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    strategyService
      .getPool()
      .then((data) => {
        if (cancelled) return;
        setItems(data);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load stock pool:", err);
        message.error("加载股票池失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const countTotal = items.length;
  const countS1 = items.filter((c) => c.strategy_type === "strategy_1").length;
  const countS2 = items.filter((c) => c.strategy_type === "strategy_2").length;

  const getScoreLabel = (item: StockPoolItem): string => {
    return item.score_total ? `${parseFloat(item.score_total).toFixed(0)}分` : "--";
  };

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
          styles={{ body: { padding: "10px", textAlign: "center" } }}
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
          styles={{ body: { padding: "10px", textAlign: "center" } }}
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
          styles={{ body: { padding: "10px", textAlign: "center" } }}
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
        dataSource={items}
        split={false}
        renderItem={(item) => {
          const decision = item.final_decision;
          const isUp = decision === "buy";
          const isDown = decision === "sell";
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
                    {item.stock_code}
                    <span
                      style={{
                        color: colors.dimmed,
                        fontSize: 11,
                        marginLeft: 6,
                      }}
                    >
                      {item.date}
                    </span>
                  </div>
                  <div
                    style={{
                      marginTop: 4,
                      display: "flex",
                      gap: 6,
                      alignItems: "center",
                    }}
                  >
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
                      {getScoreLabel(item)}
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
                      {item.strategy_type}
                    </Tag>
                  </div>
                </div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: isUp
                      ? colors.gold
                      : isDown
                      ? colors.danger
                      : colors.muted,
                    whiteSpace: "nowrap",
                  }}
                >
                  {isUp && (
                    <RiseOutlined
                      style={{ fontSize: 12, marginRight: 3 }}
                    />
                  )}
                  {isDown && (
                    <FallOutlined
                      style={{ fontSize: 12, marginRight: 3 }}
                    />
                  )}
                  {decision === "buy"
                    ? "买入"
                    : decision === "sell"
                    ? "卖出"
                    : "持有"}
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
