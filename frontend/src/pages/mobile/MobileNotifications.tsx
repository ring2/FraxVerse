import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { notificationService } from "../../services/notificationService";
import type { NotificationItem } from "../../types/api-extended";

/* ---- Mock fallback data ---- */
const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 1,
    event_type: "risk_warning",
    priority: "high",
    title: "风控预警",
    content: "宁德时代(300750) 单日跌幅超过 5%，触发止损线",
    is_read: false,
    created_at: "2026-05-02T14:30:00Z",
  },
  {
    id: 2,
    event_type: "trade_executed",
    priority: "normal",
    title: "交易执行",
    content: "贵州茅台(600519) 买入 100 股已成交，成交价 1,680.50",
    is_read: false,
    created_at: "2026-05-02T10:15:00Z",
  },
  {
    id: 3,
    event_type: "system_info",
    priority: "low",
    title: "系统通知",
    content: "日终清算已完成，今日盈亏 +28,940 (+2.3%)",
    is_read: true,
    created_at: "2026-05-01T18:00:00Z",
  },
  {
    id: 4,
    event_type: "agent_alert",
    priority: "normal",
    title: "Agent 分析完成",
    content: "今日 12 只候选股票已完成综合评分，建议关注前 3 只",
    is_read: true,
    created_at: "2026-05-01T09:00:00Z",
  },
];

/* ---- Helpers ---- */
function getPriorityColor(priority: string): string {
  const m: Record<string, string> = {
    high: "#E8735A",
    normal: "#7F77DD",
    low: "#9E9A92",
  };
  return m[priority] ?? colors.text.tertiary;
}

function getPriorityLabel(priority: string): string {
  const m: Record<string, string> = {
    high: "高",
    normal: "中",
    low: "低",
  };
  return m[priority] ?? priority;
}

function formatTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  return iso.slice(0, 10);
}

let colors: any; // placeholder, will be set inside component

function MobileNotifications() {
  const { message } = App.useApp();
  const th = useTheme();
  colors = th.colors;

  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    notificationService
      .getNotifications()
      .then((data) => {
        if (!cancelled) setNotifications(data);
      })
      .catch(() => {
        if (!cancelled) {
          setNotifications(MOCK_NOTIFICATIONS);
          message.info("已加载模拟数据（API 暂不可用）");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [message]);

  const handleMarkRead = async (id: number) => {
    try {
      await notificationService.markRead(String(id));
    } catch {
      // fallback: just update local state
    }
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
        }}
      >
        <span style={{ fontSize: 14, color: colors.text.tertiary }}>加载中...</span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <MobileSectionCard title={`通知 (${notifications.length})`}>
        {notifications.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无通知
          </div>
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              style={{
                padding: "12px 14px",
                borderBottom: `1px solid ${colors.border.light}`,
                opacity: n.is_read ? 0.6 : 1,
              }}
            >
              {/* 头部：标题 + 未读标记 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 6,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  {!n.is_read && (
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        backgroundColor: colors.semantic.amber,
                        flexShrink: 0,
                      }}
                    />
                  )}
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: colors.text.primary,
                    }}
                  >
                    {n.title}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: getPriorityColor(n.priority),
                      background: colors.bg.subtle,
                      padding: "1px 5px",
                      borderRadius: colors.radius.sm + "px",
                    }}
                  >
                    {getPriorityLabel(n.priority)}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    color: colors.text.tertiary,
                  }}
                >
                  {formatTime(n.created_at)}
                </span>
              </div>

              {/* 内容 */}
              <div
                style={{
                  fontSize: 12,
                  color: colors.text.secondary,
                  lineHeight: 1.6,
                  marginBottom: 8,
                }}
              >
                {n.content}
              </div>

              {/* 标记已读按钮 */}
              {!n.is_read && (
                <span
                  onClick={() => handleMarkRead(n.id)}
                  style={{
                    fontSize: 11,
                    color: colors.purple[500],
                    cursor: "pointer",
                    userSelect: "none",
                    padding: "2px 0",
                  }}
                >
                  标记已读
                </span>
              )}
            </div>
          ))
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileNotifications;
