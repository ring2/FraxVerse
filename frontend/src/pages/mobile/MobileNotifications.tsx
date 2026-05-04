import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { useNotificationStore, type NotificationItem } from "../../stores/useNotificationStore";

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

let colors: any;

function MobileNotifications() {
  const { message } = App.useApp();
  const th = useTheme();
  colors = th.colors;

  const notifications = useNotificationStore((s) => s.notifications);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);
  const unreadCount = useNotificationStore((s) => s.unreadCount);

  const handleMarkRead = (id: string) => {
    markRead(id);
    message.success("已标记已读");
  };

  return (
    <div
      className="page-enter"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* 全部已读按钮 */}
      {unreadCount > 0 && (
        <div
          onClick={markAllRead}
          style={{
            textAlign: "right",
            padding: "4px 14px",
            fontSize: 12,
            color: colors.purple[500],
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          全部标记已读 ({unreadCount})
        </div>
      )}

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
          notifications.map((n: NotificationItem) => (
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
                      color: getPriorityColor(n.level),
                      background: colors.bg.subtle,
                      padding: "1px 5px",
                      borderRadius: colors.radius.sm + "px",
                    }}
                  >
                    {getPriorityLabel(n.level)}
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
                {n.body}
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
                    transition: "opacity 0.15s ease",
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
