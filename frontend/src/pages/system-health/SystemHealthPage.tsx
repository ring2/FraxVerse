import { Row, Col, Card, Typography, Tag, List, Space } from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

interface Service {
  name: string;
  status: "normal" | "abnormal";
  version: string;
  uptime: string;
}

const services: Service[] = [
  { name: "FastAPI", status: "normal", version: "v2.4.1", uptime: "7天 3小时" },
  { name: "PostgreSQL", status: "normal", version: "v15.6", uptime: "14天 12小时" },
  { name: "Redis", status: "normal", version: "v7.2", uptime: "7天 3小时" },
  { name: "行情源", status: "abnormal", version: "--", uptime: "--" },
];

interface SystemEvent {
  id: string;
  time: string;
  type: string;
  message: string;
}

const recentEvents: SystemEvent[] = [
  { id: "1", time: "2026-04-29 15:30:22", type: "info", message: "收盘数据同步完成" },
  { id: "2", time: "2026-04-29 15:00:00", type: "info", message: "A股收盘，当日交易数据汇总完毕" },
  { id: "3", time: "2026-04-29 12:00:15", type: "warn", message: "行情源连接超时（重连成功）" },
  { id: "4", time: "2026-04-29 09:30:00", type: "info", message: "A股开盘，行情数据正常推送" },
  { id: "5", time: "2026-04-29 08:00:00", type: "info", message: "系统健康检查完成，所有服务运行正常" },
  { id: "6", time: "2026-04-28 23:00:00", type: "info", message: "日终清算完成" },
  { id: "7", time: "2026-04-28 15:30:00", type: "warn", message: "行情源数据延迟约2分钟" },
];

const systemUptime = "7天 3小时 42分钟";

// ─── Component ───────────────────────────────────────────────────────────────

const SystemHealthPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        系统脉搏 — 服务运行状态
      </Title>

      {/* 系统运行时间 */}
      <Card
        size="small"
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        <Space>
          <ClockCircleOutlined style={{ color: colors.shard, fontSize: 18 }} />
          <Text style={{ color: colors.muted }}>系统运行时间：</Text>
          <Text style={{ color: colors.text, fontWeight: 600, fontSize: 16 }}>
            {systemUptime}
          </Text>
        </Space>
      </Card>

      {/* 服务状态卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {services.map((svc) => (
          <Col xs={24} sm={12} lg={6} key={svc.name}>
            <Card
              style={{
                background: colors.card,
                borderColor: colors.border,
                borderRadius: 8,
              }}
              styles={{ body: { padding: 20 } }}
            >
              <Row align="middle" justify="space-between" style={{ marginBottom: 12 }}>
                <Col>
                  <Text style={{ color: colors.text, fontWeight: 600, fontSize: 15 }}>
                    {svc.name}
                  </Text>
                </Col>
                <Col>
                  <Tag
                    icon={
                      svc.status === "normal" ? (
                        <CheckCircleFilled />
                      ) : (
                        <CloseCircleFilled />
                      )
                    }
                    color={svc.status === "normal" ? colors.success : colors.danger}
                    style={{ borderRadius: 4, margin: 0 }}
                  >
                    {svc.status === "normal" ? "正常" : "异常"}
                  </Tag>
                </Col>
              </Row>
              <Space direction="vertical" size={4}>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  版本：{svc.version}
                </Text>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  运行时长：{svc.uptime}
                </Text>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 最近事件列表 */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        最近事件
      </Title>
      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: "12px 20px" } }}
      >
        <List
          dataSource={recentEvents}
          renderItem={(event) => (
            <List.Item
              style={{
                borderBottom: `1px solid ${colors.border}`,
                padding: "10px 0",
              }}
            >
              <Row align="middle" style={{ width: "100%" }}>
                <Col xs={6} sm={4}>
                  <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                    {event.time}
                  </Text>
                </Col>
                <Col xs={4} sm={3}>
                  <Tag
                    color={
                      event.type === "warn" ? colors.amber : colors.shard
                    }
                    style={{ borderRadius: 4, margin: 0, fontSize: 11 }}
                  >
                    {event.type === "warn" ? "警告" : "信息"}
                  </Tag>
                </Col>
                <Col xs={14} sm={17}>
                  <Text style={{ color: colors.muted, fontSize: 13 }}>
                    {event.message}
                  </Text>
                </Col>
              </Row>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default SystemHealthPage;
