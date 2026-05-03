import { useEffect, useState, useCallback } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { MobileSectionCard } from "../../components/mobile";
import { marketService } from "../../services/marketService";
import type { HotNewsItem } from "../../types/api-extended";

/* ---- Constants ---- */

const PAGE_SIZE = 20;

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
  if (diffMs < 0) return "刚刚";
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}天前`;
  return iso.slice(0, 10);
}

function openNews(url: string | null | undefined) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

/* ---- Component ---- */

const MobileHotNews: React.FC = () => {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [news, setNews] = useState<HotNewsItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  /** 加载数据 — append=true 时追加，否则替换 */
  const fetchNews = useCallback(
    async (append: boolean, silent: boolean) => {
      if (!silent && !append) setLoading(true);
      if (append) setLoadingMore(true);

      try {
        const offset = append ? news.length : 0;
        const result = await marketService.getNews({
          offset,
          limit: PAGE_SIZE,
        });
        const items = result.items as HotNewsItem[];
        if (append) {
          setNews((prev) => [...prev, ...items]);
        } else {
          setNews(items);
          setError(null);
        }
        setTotal(result.total);
      } catch {
        if (!append) {
          setError("获取资讯失败");
          setNews([]);
          setTotal(0);
        }
        message.info("获取资讯失败，请稍后重试");
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [message, news.length],
  );

  // 首次加载
  useEffect(() => {
    fetchNews(false, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRefresh = () => {
    // 刷新时清空 news.length 让 offset=0
    setNews([]);
    fetchNews(false, true);
  };

  const handleLoadMore = () => {
    fetchNews(true, false);
  };

  const hasMore = news.length < total;

  /* ---- Render ---- */

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
            · {total} 条
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
          {loading ? "加载中..." : "刷新"}
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
      ) : news.length === 0 ? (
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
            暂无热点资讯
            <div style={{ fontSize: 12, marginTop: 8, opacity: 0.6 }}>
              数据采集器尚未运行，新闻数据将在采集开始后自动显示
            </div>
          </div>
        </MobileSectionCard>
      ) : (
        <>
          <MobileSectionCard title={`资讯 (${news.length}/${total})`}>
            {news.map((item) => {
              const sentiment = getSentimentInfo(item.sentiment);
              const clickable = !!item.url;
              return (
                <div
                  key={item.id}
                  onClick={() => openNews(item.url)}
                  style={{
                    padding: "14px 14px",
                    borderBottom: `1px solid ${colors.border.light}`,
                    cursor: clickable ? "pointer" : "default",
                    transition: "background 0.15s",
                    WebkitTapHighlightColor: "transparent",
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
                      {item.source_display || item.source}
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

                    {item.is_hot && (
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
            })}
          </MobileSectionCard>

          {/* 加载更多 */}
          {hasMore && (
            <div
              onClick={handleLoadMore}
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                padding: "16px 0",
                cursor: "pointer",
                userSelect: "none",
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  color: colors.purple[500],
                  background: colors.bg.subtle,
                  padding: "8px 28px",
                  borderRadius: colors.radius.md + "px",
                  fontWeight: 500,
                }}
              >
                {loadingMore
                  ? "加载中..."
                  : `加载更多 (${news.length}/${total})`}
              </span>
            </div>
          )}

          {/* 已全部加载 */}
          {!hasMore && news.length > 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "16px 0 8px",
                fontSize: 12,
                color: colors.text.tertiary,
                opacity: 0.5,
              }}
            >
              — 已显示全部 {total} 条 —
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default MobileHotNews;
