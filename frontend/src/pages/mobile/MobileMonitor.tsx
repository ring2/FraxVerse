import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { useEventStore, type RiskEventItem } from "../../stores/useEventStore";

function MobileMonitor() {
  const { colors } = useTheme();
  const events = useEventStore((s) => s.events);

  /* ---- Inline helpers ---- */
  const getLevelColor = (level: string): string => {
    const m: Record<string, string> = {
      critical: colors.semantic.up,
      warning: colors.semantic.amber,
      info: colors.text.secondary,
    };
    return m[level] ?? colors.text.secondary;
  };

  const getLevelBg = (level: string): string => {
    const m: Record<string, string> = {
      critical: colors.semantic.upBg,
      warning: colors.semantic.amberBg,
      info: colors.bg.subtle,
    };
    return m[level] ?? colors.bg.subtle;
  };

  const getLevelLabel = (level: string): string => {
    const m: Record<string, string> = {
      critical: "严重",
      warning: "警告",
      info: "提示",
    };
    return m[level] ?? level;
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
      {/* 风控事件列表（实时） */}
      <MobileSectionCard title={`风控事件 (${events.length})`}>
        {events.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无风控事件
          </div>
        ) : (
          events.map((evt: RiskEventItem) => (
            <div
              key={evt.id}
              style={{
                padding: "12px 14px",
                borderBottom: `1px solid ${colors.border.light}`,
              }}
            >
              {/* 头部：事件类型 + 级别 */}
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
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: colors.text.primary,
                    }}
                  >
                    {evt.event_type}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: getLevelColor(evt.event_level),
                      background: getLevelBg(evt.event_level),
                      padding: "1px 6px",
                      borderRadius: colors.radius.sm + "px",
                      fontWeight: 500,
                    }}
                  >
                    {getLevelLabel(evt.event_level)}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    color: colors.text.tertiary,
                  }}
                >
                  {evt.created_at?.slice(0, 16).replace("T", " ") ?? ""}
                </span>
              </div>

              {/* 触发原因 */}
              <div
                style={{
                  fontSize: 12,
                  color: colors.text.secondary,
                  lineHeight: 1.6,
                  marginBottom: 4,
                }}
              >
                {evt.trigger_reason}
              </div>

              {/* 处置措施 */}
              <div
                style={{
                  fontSize: 11,
                  color: colors.text.tertiary,
                }}
              >
                处置: {evt.action_taken}
              </div>
            </div>
          ))
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileMonitor;
