import { useEffect, useState, useCallback } from "react";
import { Card, Typography, List, Tag, Space, Button, App } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  BellOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { notificationService } from "../../services/notificationService";
import type { NotificationItem } from "../../types/api-extended";

const { Title, Text } = Typography;

// ─── Config ───────────────────────────────────────────────────────────────────

const typeConfig: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  trade: {
    color: colors.shard,
    icon: <CheckCircleOutlined />,
    label: "成交",
  },
  stop_loss: {
    color: colors.danger,
    icon: <CloseCircleOutlined />,
    label: "止损",
  },
  alert: {
    color: colors.amber,
    icon: <WarningOutlined />,
    label: "预警",
  },
  system: {
    color: colors.nebula,
    icon: <BellOutlined />,
    label: "系统",
  },
};

/** 根据优先级返回合适颜色 */
function priorityColor(priority: string): string | undefined {
  if (priority === "high" || priority === "critical") return colors.danger;
  if (priority === "medium") return colors.amber;
  return undefined; // low / normal → 不覆盖
}

// ─── Component ───────────────────────────────────────────────────────────────

const NotificationPage: React.FC = () => {
  const { message } = App.useApp();

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await notificationService.getNotifications();
      setNotifications(data);
    } catch (err) {
      console.error("获取通知失败", err);
      message.error("获取通知失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkRead = async (id: number) => {
    try {
      await notificationService.markRead(String(id));
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      message.success("已标记为已读");
    } catch (err) {
      console.error("标记已读失败", err);
      message.error("标记已读失败");
    }
  };

  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        回音 — 消息通知
      </Title>

      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: "12px 20px" } }}
      >
        {loading ? (
          <Text style={{ color: colors.dimmed }}>加载中…</Text>
        ) : notifications.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <BellOutlined
              style={{ fontSize: 48, color: colors.dimmed, marginBottom: 16 }}
            />
            <br />
            <Text style={{ color: colors.dimmed, fontSize: 14 }}>
              <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无通知消息——有新消息时你将收到推送</Text>
            </Text>
          </div>
        ) : (
          <List
            dataSource={notifications}
            renderItem={(item) => {
              const cfg = typeConfig[item.event_type] ?? {
                color: colors.nebula,
                icon: <BellOutlined />,
                label: item.event_type,
              };
              const priColor = priorityColor(item.priority);

              return (
                <List.Item
                  style={{
                    borderBottom: `1px solid ${colors.border}`,
                    padding: "14px 0",
                    background: item.is_read ? "transparent" : colors.surface,
                    borderRadius: 4,
                    marginBottom: 2,
                    paddingLeft: item.is_read ? 0 : 8,
                    transition: "background 0.2s",
                  }}
                  actions={
                    !item.is_read
                      ? [
                          <Button
                            type="link"
                            size="small"
                            onClick={() => handleMarkRead(item.id)}
                            style={{ color: colors.shard, fontSize: 12 }}
                          >
                            标为已读
                          </Button>,
                        ]
                      : undefined
                  }
                >
                  <List.Item.Meta
                    avatar={
                      <Space size={4}>
                        <Tag
                          icon={cfg.icon}
                          color={cfg.color}
                          style={{
                            borderRadius: 4,
                            margin: 0,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {cfg.label}
                        </Tag>
                        {priColor && (
                          <Tag
                            color={priColor}
                            style={{
                              borderRadius: 4,
                              margin: 0,
                              fontSize: 10,
                              padding: "0 4px",
                              lineHeight: "18px",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {item.priority === "critical"
                              ? "紧急"
                              : item.priority === "high"
                                ? "高"
                                : item.priority === "medium"
                                  ? "中"
                                  : "低"}
                          </Tag>
                        )}
                      </Space>
                    }
                    title={
                      <Space size={12}>
                        <Text
                          style={{
                            color: colors.text,
                            fontWeight: item.is_read ? 400 : 600,
                            fontSize: 14,
                          }}
                        >
                          {item.title}
                        </Text>
                        <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleString("zh-CN")
                            : ""}
                        </Text>
                      </Space>
                    }
                    description={
                      <Text
                        style={{
                          color: colors.muted,
                          fontSize: 13,
                          lineHeight: 1.6,
                        }}
                      >
                        {item.content}
                      </Text>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default NotificationPage;
