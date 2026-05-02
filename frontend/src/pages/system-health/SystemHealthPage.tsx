import { useEffect, useState } from "react";
import { Row, Col, Card, Typography, Tag, List, Space, App } from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { monitorService } from "../../services/monitorService";
import type { ServiceStatus, SystemResource } from "../../types/api-extended";

const { Title, Text } = Typography;

/** 将 uptime_seconds 转为 "X天X小时" 格式 */
function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "--";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) return `${days}天 ${hours}小时`;
  return `${hours}小时`;
}

// ─── Component ───────────────────────────────────────────────────────────────

const SystemHealthPage: React.FC = () => {
  const { message } = App.useApp();

  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [resources, setResources] = useState<SystemResource | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetch() {
      try {
        const [svcRes, resRes] = await Promise.allSettled([
          monitorService.getServices(),
          monitorService.getResources(),
        ]);

        if (cancelled) return;

        if (svcRes.status === "fulfilled") {
          setServices(svcRes.value);
        } else {
          console.warn("获取服务状态失败", svcRes.reason);
          message.error("获取服务状态失败");
        }

        if (resRes.status === "fulfilled") {
          setResources(resRes.value);
        } else {
          console.warn("获取系统资源失败（后端可能缺少 psutil）", resRes.reason);
          setResources(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetch();
    return () => {
      cancelled = true;
    };
  }, [message]);

  // 计算系统运行时长（从所有服务 uptime 中取最大值）
  const systemUptimeStr = (() => {
    const maxSec = Math.max(
      0,
      ...services.map((s) => s.uptime_seconds ?? 0)
    );
    return formatUptime(maxSec > 0 ? maxSec : null);
  })();

  // 组装最近事件（从服务 last_error 生成）
  const recentEvents: { id: string; time: string; message: string }[] =
    services
      .filter((s) => s.last_error)
      .map((s, i) => ({
        id: `err-${i}`,
        time: "",
        message: `${s.service}：${s.last_error!}`,
      }));

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
            {loading ? "加载中…" : systemUptimeStr}
          </Text>
        </Space>
      </Card>

      {/* 服务状态卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {loading
          ? // 加载骨架
            Array.from({ length: 4 }).map((_, i) => (
              <Col xs={24} sm={12} lg={6} key={`skeleton-${i}`}>
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
          : services.length === 0
            ? // 空状态
              (
                <Col span={24}>
                  <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无服务数据——系统可能未完全启动</Text>
                </Col>
              )
            : services.map((svc) => (
                <Col xs={24} sm={12} lg={6} key={svc.service}>
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
                      style={{ marginBottom: 12 }}
                    >
                      <Col>
                        <Text
                          style={{
                            color: colors.text,
                            fontWeight: 600,
                            fontSize: 15,
                          }}
                        >
                          {svc.service}
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
                          color={
                            svc.status === "normal"
                              ? colors.success
                              : colors.danger
                          }
                          style={{ borderRadius: 4, margin: 0 }}
                        >
                          {svc.status === "normal" ? "正常" : "异常"}
                        </Tag>
                      </Col>
                    </Row>
                    <Space direction="vertical" size={4}>
                      <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                        运行时长：{formatUptime(svc.uptime_seconds)}
                      </Text>
                      {svc.last_error && (
                        <Text style={{ color: colors.danger, fontSize: 12 }}>
                          最近错误：{svc.last_error}
                        </Text>
                      )}
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
        {recentEvents.length === 0 ? (
          <Text style={{ color: colors.dimmed, fontSize: 13 }}>
            <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无事件记录</Text>
          </Text>
        ) : (
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
                  <Col xs={4} sm={3}>
                    <Tag
                      color={colors.danger}
                      style={{ borderRadius: 4, margin: 0, fontSize: 11 }}
                    >
                      异常
                    </Tag>
                  </Col>
                  <Col xs={20} sm={21}>
                    <Text style={{ color: colors.muted, fontSize: 13 }}>
                      {event.message}
                    </Text>
                  </Col>
                </Row>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 系统资源摘要 */}
      <Title
        level={5}
        style={{ color: colors.muted, marginBottom: 12, marginTop: 24 }}
      >
        系统资源
      </Title>
      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: 20 } }}
      >
        {resources ? (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Text style={{ color: colors.dimmed, fontSize: 12 }}>CPU</Text>
              <br />
              <Text style={{ color: colors.text, fontWeight: 600, fontSize: 16 }}>
                {resources.cpu_percent?.toFixed(1) ?? "--"}%
              </Text>
            </Col>
            <Col xs={12} sm={6}>
              <Text style={{ color: colors.dimmed, fontSize: 12 }}>内存</Text>
              <br />
              <Text style={{ color: colors.text, fontWeight: 600, fontSize: 16 }}>
                {resources.memory_percent?.toFixed(1) ?? "--"}%
              </Text>
            </Col>
            <Col xs={12} sm={6}>
              <Text style={{ color: colors.dimmed, fontSize: 12 }}>内存使用</Text>
              <br />
              <Text style={{ color: colors.text, fontWeight: 600, fontSize: 16 }}>
                {resources.memory_mb?.toFixed(0) ?? "--"} MB
              </Text>
            </Col>
            <Col xs={12} sm={6}>
              <Text style={{ color: colors.dimmed, fontSize: 12 }}>磁盘</Text>
              <br />
              <Text style={{ color: colors.text, fontWeight: 600, fontSize: 16 }}>
                {resources.disk_percent?.toFixed(1) ?? "--"}%
              </Text>
            </Col>
          </Row>
        ) : (
          <Text style={{ color: colors.dimmed, fontSize: 13 }}>
            <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无资源数据（后端可能缺少 psutil）</Text>
          </Text>
        )}
      </Card>
    </div>
  );
};

export default SystemHealthPage;
