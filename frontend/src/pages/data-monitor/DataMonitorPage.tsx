import { Row, Col, Card, Typography, Tag, Descriptions, Space } from "antd";
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

interface CollectorStatus {
  name: string;
  status: "normal" | "delayed" | "abnormal";
  label: string;
}

const collectors: CollectorStatus[] = [
  { name: "K线数据", status: "normal", label: "正常" },
  { name: "板块数据", status: "normal", label: "正常" },
  { name: "资金流", status: "delayed", label: "延迟10min" },
  { name: "新闻数据", status: "normal", label: "正常" },
];

interface TableQuality {
  name: string;
  rowCount: number;
  latestTime: string;
  nullRate: number;
}

const tableQualities: TableQuality[] = [
  { name: "daily_kline", rowCount: 52846, latestTime: "2026-04-29 15:00", nullRate: 0.02 },
  { name: "sector_index", rowCount: 8320, latestTime: "2026-04-29 15:00", nullRate: 0.01 },
  { name: "money_flow", rowCount: 15320, latestTime: "2026-04-29 14:50", nullRate: 0.05 },
  { name: "news_article", rowCount: 28410, latestTime: "2026-04-29 15:20", nullRate: 0.08 },
  { name: "fund_holdings", rowCount: 125600, latestTime: "2026-04-28 23:00", nullRate: 0.15 },
  { name: "block_trade", rowCount: 4460, latestTime: "2026-04-29 15:00", nullRate: 0.03 },
];

// ─── Component ───────────────────────────────────────────────────────────────

const DataMonitorPage: React.FC = () => {
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
        {collectors.map((col) => {
          let tagColor: string;
          let icon: React.ReactNode;
          if (col.status === "normal") {
            tagColor = colors.success;
            icon = <CheckCircleFilled />;
          } else if (col.status === "delayed") {
            tagColor = colors.amber;
            icon = <ClockCircleOutlined />;
          } else {
            tagColor = colors.danger;
            icon = <WarningOutlined />;
          }

          return (
            <Col xs={24} sm={12} lg={6} key={col.name}>
              <Card
                style={{
                  background: colors.card,
                  borderColor: colors.border,
                  borderRadius: 8,
                }}
                styles={{ body: { padding: 20 } }}
              >
                <Row align="middle" justify="space-between" style={{ marginBottom: 8 }}>
                  <Col>
                    <Text style={{ color: colors.text, fontWeight: 600, fontSize: 15 }}>
                      {col.name}
                    </Text>
                  </Col>
                  <Col>
                    <Tag
                      icon={icon}
                      color={tagColor}
                      style={{ borderRadius: 4, margin: 0 }}
                    >
                      {col.label}
                    </Tag>
                  </Col>
                </Row>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  {col.status === "normal"
                    ? "数据实时同步中"
                    : col.status === "delayed"
                      ? "数据存在延迟"
                      : "采集异常"}
                </Text>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* 数据质量 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        数据质量
      </Title>
      <Row gutter={[16, 16]}>
        {tableQualities.map((tq) => (
          <Col xs={24} sm={12} lg={8} key={tq.name}>
            <Card
              size="small"
              style={{
                background: colors.card,
                borderColor: colors.border,
                borderRadius: 8,
              }}
              styles={{ body: { padding: 16 } }}
            >
              <Text style={{ color: colors.shard, fontWeight: 600, fontSize: 14, display: "block", marginBottom: 12 }}>
                {tq.name}
              </Text>
              <Descriptions
                column={1}
                size="small"
                style={{
                  background: colors.surface,
                  borderRadius: 8,
                  padding: 12,
                }}
              >
                <Descriptions.Item label="数据行数">
                  {tq.rowCount.toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="最新时间">
                  {tq.latestTime}
                </Descriptions.Item>
                <Descriptions.Item label="空值率">
                  <Space size={4}>
                    <Text style={{ color: tq.nullRate > 0.1 ? colors.amber : colors.text }}>
                      {tq.nullRate.toFixed(2)}%
                    </Text>
                    {tq.nullRate > 0.1 && (
                      <WarningOutlined style={{ color: colors.amber, fontSize: 12 }} />
                    )}
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default DataMonitorPage;
