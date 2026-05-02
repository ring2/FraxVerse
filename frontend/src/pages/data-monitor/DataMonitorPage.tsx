import { useEffect, useState } from "react";
import { Row, Col, Card, Typography, Tag, Space, App } from "antd";
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { marketService } from "../../services/marketService";
import { riskService } from "../../services/riskService";
import type {
  MarketStateResponse,
  SectorItem,
  NewsItem,
  RiskMetricsItem,
} from "../../types/api-extended";

const { Title, Text } = Typography;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  if (status === "normal" || status === "trading") return colors.success;
  if (status === "delayed" || status === "closed") return colors.amber;
  return colors.danger;
}

function statusIcon(status: string): React.ReactNode {
  if (status === "normal" || status === "trading") return <CheckCircleFilled />;
  if (status === "delayed" || status === "closed")
    return <ClockCircleOutlined />;
  return <WarningOutlined />;
}

function statusLabel(status: string): string {
  if (status === "normal") return "正常";
  if (status === "trading") return "交易中";
  if (status === "delayed") return "延迟";
  if (status === "closed") return "已收盘";
  return status;
}

function statusHint(status: string): string {
  if (status === "normal" || status === "trading") return "数据实时同步中";
  if (status === "delayed") return "数据存在延迟";
  if (status === "closed") return "今日已收盘";
  return "采集异常";
}

// ─── Component ───────────────────────────────────────────────────────────────

const DataMonitorPage: React.FC = () => {
  const { message } = App.useApp();

  const [marketState, setMarketState] = useState<MarketStateResponse | null>(
    null
  );
  const [sectors, setSectors] = useState<SectorItem[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [metrics, setMetrics] = useState<RiskMetricsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetch() {
      try {
        const [stateRes, sectorsRes, newsRes, metricsRes] =
          await Promise.allSettled([
            marketService.getMarketState(),
            marketService.getSectors(),
            marketService.getNews(),
            riskService.getMetrics(),
          ]);

        if (cancelled) return;

        if (stateRes.status === "fulfilled") setMarketState(stateRes.value);
        else console.warn("获取市场状态失败", stateRes.reason);

        if (sectorsRes.status === "fulfilled") setSectors(sectorsRes.value);
        else console.warn("获取板块数据失败", sectorsRes.reason);

        if (newsRes.status === "fulfilled") setNews(newsRes.value);
        else console.warn("获取新闻数据失败", newsRes.reason);

        if (metricsRes.status === "fulfilled") setMetrics(metricsRes.value);
        else console.warn("获取风控指标失败", metricsRes.reason);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetch();
    return () => {
      cancelled = true;
    };
  }, [message]);

  // 组装采集器状态卡片（基于市场状态 + 风控指标）
  const collectorCards = [
    {
      name: "K线数据",
      status: marketState ? "trading" : "delayed",
      label: marketState
        ? `${
            marketState.current_state === "trading" ? "正常" : "已收盘"
          }`
        : "暂无数据",
    },
    {
      name: "板块数据",
      status: sectors.length > 0 ? "normal" : "delayed",
      label: sectors.length > 0 ? "正常" : "暂无数据",
    },
    {
      name: "风控指标",
      status: metrics.length > 0 ? "normal" : "delayed",
      label: metrics.length > 0 ? "正常" : "暂无数据",
    },
    {
      name: "新闻数据",
      status: news.length > 0 ? "normal" : "delayed",
      label: news.length > 0 ? "正常" : "暂无数据",
    },
  ];

  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        天眼 — 数据采集监控
      </Title>

      {/* 采集状态 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        采集状态
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Col xs={24} sm={12} lg={6} key={`skel-${i}`}>
                <Card
                  style={{
                    background: colors.card,
                    borderColor: colors.border,
                    borderRadius: 8,
                  }}
                  styles={{ body: { padding: 20 } }}
                >
                  <Text style={{ color: colors.dimmed }}>加载中…</Text>
                </Card>
              </Col>
            ))
          : collectorCards.map((col) => (
              <Col xs={24} sm={12} lg={6} key={col.name}>
                <Card
                  style={{
                    background: colors.card,
                    borderColor: colors.border,
                    borderRadius: 8,
                  }}
                  styles={{ body: { padding: 20 } }}
                >
                  <Row
                    align="middle"
                    justify="space-between"
                    style={{ marginBottom: 8 }}
                  >
                    <Col>
                      <Text
                        style={{
                          color: colors.text,
                          fontWeight: 600,
                          fontSize: 15,
                        }}
                      >
                        {col.name}
                      </Text>
                    </Col>
                    <Col>
                      <Tag
                        icon={statusIcon(col.status)}
                        color={statusColor(col.status)}
                        style={{ borderRadius: 4, margin: 0 }}
                      >
                        {col.label}
                      </Tag>
                    </Col>
                  </Row>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    {statusHint(col.status)}
                  </Text>
                </Card>
              </Col>
            ))}
      </Row>

      {/* 市场概况 */}
      {marketState && (
        <>
          <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
            市场概况
          </Title>
          <Card
            size="small"
            style={{
              background: colors.card,
              borderColor: colors.border,
              borderRadius: 8,
              marginBottom: 24,
            }}
            styles={{ body: { padding: 16 } }}
          >
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  交易日期
                </Text>
                <br />
                <Text
                  style={{ color: colors.text, fontWeight: 600, fontSize: 14 }}
                >
                  {marketState.date ?? "--"}
                </Text>
              </Col>
              <Col xs={12} sm={6}>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  市场状态
                </Text>
                <br />
                <Tag
                  color={statusColor(marketState.current_state)}
                  style={{ borderRadius: 4, marginTop: 2 }}
                >
                  {statusLabel(marketState.current_state)}
                </Tag>
              </Col>
              <Col xs={12} sm={6}>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  主线板块
                </Text>
                <br />
                <Text
                  style={{ color: colors.text, fontWeight: 600, fontSize: 14 }}
                >
                  {marketState.main_line_sector ?? "--"}
                </Text>
              </Col>
              <Col xs={12} sm={6}>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  置信度
                </Text>
                <br />
                <Text
                  style={{ color: colors.text, fontWeight: 600, fontSize: 14 }}
                >
                  {marketState.confidence != null
                    ? `${marketState.confidence}%`
                    : "--"}
                </Text>
              </Col>
            </Row>
          </Card>
        </>
      )}

      {/* 板块概览 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        板块概览
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {sectors.length === 0 ? (
          <Col span={24}>
            <Card
              size="small"
              style={{
                background: colors.card,
                borderColor: colors.border,
                borderRadius: 8,
              }}
              styles={{ body: { padding: 16 } }}
            >
              <Text style={{ color: colors.dimmed, fontSize: 13 }}>
                暂无板块数据
              </Text>
            </Card>
          </Col>
        ) : (
          sectors.slice(0, 6).map((s) => (
            <Col xs={24} sm={12} lg={8} key={s.sector_name}>
              <Card
                size="small"
                style={{
                  background: colors.card,
                  borderColor: colors.border,
                  borderRadius: 8,
                }}
                styles={{ body: { padding: 16 } }}
              >
                <Text
                  style={{
                    color: colors.shard,
                    fontWeight: 600,
                    fontSize: 14,
                    display: "block",
                    marginBottom: 8,
                  }}
                >
                  {s.sector_name}
                </Text>
                <Space direction="vertical" size={4}>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    类型：{s.sector_type}
                  </Text>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    涨幅：{s.change_pct ?? "--"}
                  </Text>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    资金占比：{s.capital_ratio ?? "--"}
                  </Text>
                  {s.leader_stocks && s.leader_stocks.length > 0 && (
                    <Text style={{ color: colors.muted, fontSize: 12 }}>
                      领涨：{s.leader_stocks.join("、")}
                    </Text>
                  )}
                </Space>
              </Card>
            </Col>
          ))
        )}
      </Row>

      {/* 新闻速览 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        新闻速览
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {news.length === 0 ? (
          <Col span={24}>
            <Card
              size="small"
              style={{
                background: colors.card,
                borderColor: colors.border,
                borderRadius: 8,
              }}
              styles={{ body: { padding: 16 } }}
            >
              <Text style={{ color: colors.dimmed, fontSize: 13 }}>
                暂无新闻数据
              </Text>
            </Card>
          </Col>
        ) : (
          news.slice(0, 4).map((n) => (
            <Col xs={24} key={n.id}>
              <Card
                size="small"
                style={{
                  background: colors.card,
                  borderColor: colors.border,
                  borderRadius: 8,
                }}
                styles={{ body: { padding: "10px 16px" } }}
              >
                <Space direction="vertical" size={2}>
                  <Space size={8}>
                    <Text
                      style={{
                        color: colors.text,
                        fontWeight: 500,
                        fontSize: 13,
                      }}
                    >
                      {n.title}
                    </Text>
                    {n.is_hot && (
                      <Tag
                        color={colors.danger}
                        style={{
                          borderRadius: 4,
                          fontSize: 10,
                          lineHeight: "16px",
                          padding: "0 4px",
                        }}
                      >
                        热门
                      </Tag>
                    )}
                  </Space>
                  <Space size={12}>
                    <Text style={{ color: colors.dimmed, fontSize: 11 }}>
                      {n.source}
                    </Text>
                    <Text style={{ color: colors.dimmed, fontSize: 11 }}>
                      {n.published_at
                        ? new Date(n.published_at).toLocaleString("zh-CN")
                        : ""}
                    </Text>
                    {n.sentiment && (
                      <Text style={{ color: colors.muted, fontSize: 11 }}>
                        情绪：{n.sentiment}
                      </Text>
                    )}
                  </Space>
                </Space>
              </Card>
            </Col>
          ))
        )}
      </Row>

      {/* 风控指标 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        风控指标
      </Title>
      <Row gutter={[16, 16]}>
        {metrics.length === 0 ? (
          <Col span={24}>
            <Card
              size="small"
              style={{
                background: colors.card,
                borderColor: colors.border,
                borderRadius: 8,
              }}
              styles={{ body: { padding: 16 } }}
            >
              <Text style={{ color: colors.dimmed, fontSize: 13 }}>
                暂无风控指标数据
              </Text>
            </Card>
          </Col>
        ) : (
          metrics.slice(0, 3).map((m, i) => (
            <Col xs={24} sm={12} lg={8} key={m.trade_date + "-" + i}>
              <Card
                size="small"
                style={{
                  background: colors.card,
                  borderColor: colors.border,
                  borderRadius: 8,
                }}
                styles={{ body: { padding: 16 } }}
              >
                <Text
                  style={{
                    color: colors.shard,
                    fontWeight: 600,
                    fontSize: 14,
                    display: "block",
                    marginBottom: 8,
                  }}
                >
                  {m.trade_date}
                </Text>
                <Space direction="vertical" size={4}>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    日回撤：{m.daily_drawdown ?? "--"}
                  </Text>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    胜率：{m.win_rate ?? "--"}
                  </Text>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    连亏天数：{m.consecutive_loss_days ?? 0}
                  </Text>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    总仓位：{m.total_position_pct ?? "--"}
                  </Text>
                  <Tag
                    color={
                      m.risk_status === "normal" || m.risk_status === "safe"
                        ? colors.success
                        : colors.amber
                    }
                    style={{ borderRadius: 4, margin: 0, fontSize: 11 }}
                  >
                    {m.risk_status === "normal" || m.risk_status === "safe"
                      ? "安全"
                      : "关注"}
                  </Tag>
                </Space>
              </Card>
            </Col>
          ))
        )}
      </Row>
    </div>
  );
};

export default DataMonitorPage;
