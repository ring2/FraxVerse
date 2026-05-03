import { useEffect, useState, useCallback } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { marketService } from "../../services/marketService";
import type { NewsItem } from "../../types/api-extended";

/* ---- Helpers ---- */

function getSentimentInfo(sentiment: string | null | undefined): {
  label: string;
  color: string;
} {
  const m: Record<string, { label: string; color: string }> = {
    positive: { label: "利好", color: "#E8735A" },
    negative: { label: "利空", color: "#4DB899" },
    neutral: { label: "中性", color: "#9E9A92" },
  };
  const key = sentiment?.toLowerCase() ?? "";
  return m[key] ?? { label: "中性", color: "#9E9A92" };
}

function formatTimeAgo(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}天前`;
  return iso.slice(0, 10);
}

function sourceDisplay(source: string): string {
  const m: Record<string, string> = {
    akshare: "财经资讯",
    eastmoney: "东方财富",
    wallstreet: "华尔街见闻",
    sina: "新浪财经",
  };
  return m[source] ?? source;
}

const MobileHotNews: React.FC = () => {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      setError(null);
      try {
        const data = await marketService.getNews();
        setNews(data);
        if (data.length === 0 && !silent) {
          message.info("暂无热点资讯，稍后再来看看吧");
        }
      } catch {
        setError("获取资讯失败");
        if (!silent) {
          message.info("获取资讯失败，请稍后重试");
        }
        setNews([]);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [message],
  );

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchNews(true);
  };

  return (
    <div className="page-enter" style={{ paddingBottom: 16 }}>
      {/* Header */}
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          marginBottom: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              background: "linear-gradient(135deg, #E8735A, #D45A40)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            热闻感知
          </span>
          <span
            style={{
              fontSize: 11,
              color: colors.text.tertiary,
              fontWeight: 400,
            }}
          >
            · 市场的心念
          </span>
        </div>
        <span
          onClick={handleRefresh}
          style={{
            fontSize: 12,
            color: colors.purple[500],
            cursor: "pointer",
            userSelect: "none",
            padding: "4px 10px",
            borderRadius: colors.radius.sm + "px",
            background: colors.bg.subtle,
          }}
        >
          {refreshing ? "刷新中..." : "刷新"}
        </span>
      </div>

      {loading ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "60vh",
          }}
        >
          <span style={{ fontSize: 14, color: colors.text.tertiary }}>
            加载中...
          </span>
        </div>
      ) : error ? (
        <MobileSectionCard title="热闻感知">
          <div
            style={{
              padding: "40px 14px",
              textAlign: "center",
              color: colors.text.tertiary,
              fontSize: 13,
              lineHeight: 1.8,
            }}
          >
            {error}
            <div style={{ fontSize: 12, marginTop: 8, opacity: 0.6 }}>
              点右上角刷新重试
            </div>
          </div>
        </MobileSectionCard>
      ) : (
        <MobileSectionCard title={`资讯 (${news.length})`}>
          {news.length === 0 ? (
            <div
              style={{
                padding: "40px 14px",
                textAlign: "center",
                color: colors.text.tertiary,
                fontSize: 13,
                lineHeight: 1.8,
              }}
            >
              暂无热点资讯
              <div style={{ fontSize: 12, marginTop: 8, opacity: 0.6 }}>
                数据采集器尚未运行，新闻数据将在采集开始后自动显示
              </div>
            </div>
          ) : (
            news.map((item) => {
              const sentiment = getSentimentInfo(item.sentiment);
              return (
                <div
                  key={item.id}
                  style={{
                    padding: "14px 14px",
                    borderBottom: `1px solid ${colors.border.light}`,
                  }}
                >
                  {/* 来源 + 时间 */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 6,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        color: colors.text.tertiary,
                      }}
                    >
                      {sourceDisplay(item.source)}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        color: colors.text.tertiary,
                      }}
                    >
                      {formatTimeAgo(item.published_at)}
                    </span>
                  </div>

                  {/* 标题 */}
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: colors.text.primary,
                      lineHeight: 1.5,
                      marginBottom: 8,
                    }}
                  >
                    {item.title}
                  </div>

                  {/* 底部：情感标签 + 关联股票 */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        color: sentiment.color,
                        background: `${sentiment.color}18`,
                        padding: "1px 6px",
                        borderRadius: 3,
                        fontWeight: 500,
                      }}
                    >
                      {sentiment.label}
                    </span>

                    {/* 热点标记 */}
                    {(item as any).is_hot && (
                      <span
                        style={{
                          fontSize: 10,
                          color: "#E8735A",
                          background: "#E8735A18",
                          padding: "1px 6px",
                          borderRadius: 3,
                          fontWeight: 500,
                        }}
                      >
                        热门
                      </span>
                    )}

                    {/* 关联股票 */}
                    {item.related_stocks &&
                      item.related_stocks.slice(0, 3).map((stock) => (
                        <span
                          key={stock}
                          style={{
                            fontSize: 10,
                            color: colors.purple[500],
                            background: colors.bg.subtle,
                            padding: "1px 6px",
                            borderRadius: 3,
                            fontFamily: "monospace",
                          }}
                        >
                          {stock}
                        </span>
                      ))}
                  </div>
                </div>
              );
            })
          )}
        </MobileSectionCard>
      )}
    </div>
  );
};

export default MobileHotNews;
