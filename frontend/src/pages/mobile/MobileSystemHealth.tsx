import { useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { monitorService } from "../../services/monitorService";
import type { ServiceStatus, SystemResource } from "../../types/api-extended";

/* ---- Mock fallback data ---- */
const MOCK_SERVICES: ServiceStatus[] = [
  { service: "API Server", status: "healthy", uptime_seconds: 259200, last_error: null },
  { service: "Agent Engine", status: "healthy", uptime_seconds: 172800, last_error: null },
  { service: "Market Data", status: "degraded", uptime_seconds: 86400, last_error: "Redis 连接超时，使用本地缓存" },
  { service: "Database", status: "healthy", uptime_seconds: 259200, last_error: null },
  { service: "Risk Control", status: "healthy", uptime_seconds: 259200, last_error: null },
  { service: "Notification", status: "healthy", uptime_seconds: 259200, last_error: null },
];

const MOCK_RESOURCES: SystemResource = {
  cpu_percent: 45,
  memory_percent: 62,
  memory_mb: 4096,
  disk_percent: 71,
};

/* ---- Helpers ---- */
function getStatusColor(status: string): string {
  const m: Record<string, string> = {
    healthy: colors.semantic.down,
    degraded: colors.semantic.amber,
    down: colors.semantic.up,
  };
  return m[status] ?? colors.text.tertiary;
}

function getStatusBg(status: string): string {
  const m: Record<string, string> = {
    healthy: colors.semantic.downBg,
    degraded: colors.semantic.amberBg,
    down: colors.semantic.upBg,
  };
  return m[status] ?? colors.bg.subtle;
}

function getStatusLabel(status: string): string {
  const m: Record<string, string> = {
    healthy: "正常",
    degraded: "降级",
    down: "宕机",
  };
  return m[status] ?? status;
}

function formatUptime(seconds: number | null | undefined): string {
  if (!seconds && seconds !== 0) return "-";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) return `${days}d ${hours}h`;
  return `${hours}h`;
}

function resourceBarColor(pct: number): string {
  if (pct >= 80) return colors.semantic.up;
  if (pct >= 60) return colors.semantic.amber;
  return colors.semantic.down;
}

function MobileSystemHealth() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [resources, setResources] = useState<SystemResource | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      monitorService.getServices().catch(() => MOCK_SERVICES),
      monitorService.getResources().catch(() => MOCK_RESOURCES),
    ])
      .then(([s, r]) => {
        if (!cancelled) {
          setServices(s);
          setResources(r);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setServices(MOCK_SERVICES);
          setResources(MOCK_RESOURCES);
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
      {/* 系统资源 */}
      <MobileSectionCard title="系统资源">
        {resources ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 14,
              padding: "12px 14px",
            }}
          >
            {/* CPU */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <span style={{ fontSize: 12, color: colors.text.secondary }}>CPU</span>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: resourceBarColor(resources.cpu_percent),
                  }}
                >
                  {resources.cpu_percent}%
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  background: colors.border.light,
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${resources.cpu_percent}%`,
                    height: "100%",
                    background: resourceBarColor(resources.cpu_percent),
                    borderRadius: 2,
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>

            {/* 内存 */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <span style={{ fontSize: 12, color: colors.text.secondary }}>
                  内存 ({resources.memory_mb} MB)
                </span>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: resourceBarColor(resources.memory_percent),
                  }}
                >
                  {resources.memory_percent}%
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  background: colors.border.light,
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${resources.memory_percent}%`,
                    height: "100%",
                    background: resourceBarColor(resources.memory_percent),
                    borderRadius: 2,
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>

            {/* 磁盘 */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <span style={{ fontSize: 12, color: colors.text.secondary }}>磁盘</span>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: resourceBarColor(resources.disk_percent),
                  }}
                >
                  {resources.disk_percent}%
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  background: colors.border.light,
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${resources.disk_percent}%`,
                    height: "100%",
                    background: resourceBarColor(resources.disk_percent),
                    borderRadius: 2,
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无资源数据
          </div>
        )}
      </MobileSectionCard>

      {/* 服务状态 */}
      <MobileSectionCard title={`服务状态 (${services.length})`}>
        {services.length === 0 ? (
          <div
            style={{
              padding: "24px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
            }}
          >
            暂无服务数据
          </div>
        ) : (
          services.map((svc, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                flexDirection: "column",
                padding: "10px 14px",
                borderBottom: `1px solid ${colors.border.light}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  {/* 状态点 */}
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: getStatusColor(svc.status),
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: colors.text.primary,
                    }}
                  >
                    {svc.service}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      color: getStatusColor(svc.status),
                      background: getStatusBg(svc.status),
                      padding: "1px 7px",
                      borderRadius: colors.radius.sm + "px",
                      fontWeight: 500,
                    }}
                  >
                    {getStatusLabel(svc.status)}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: colors.text.tertiary,
                    }}
                  >
                    {formatUptime(svc.uptime_seconds)}
                  </span>
                </div>
              </div>
              {svc.last_error && (
                <div
                  style={{
                    marginTop: 4,
                    marginLeft: 16,
                    fontSize: 11,
                    color: colors.semantic.amber,
                    lineHeight: 1.5,
                  }}
                >
                  {svc.last_error}
                </div>
              )}
            </div>
          ))
        )}
      </MobileSectionCard>
    </div>
  );
}

export default MobileSystemHealth;
