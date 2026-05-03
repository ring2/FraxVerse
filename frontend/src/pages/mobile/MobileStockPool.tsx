import { useCallback, useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
  StockDetailDrawer,
} from "../../components/mobile";
import { strategyService } from "../../services/strategyService";

const STRATEGY_FILTERS = ["全部", "周期底部", "趋势低吸"];

const STRATEGY_NAMES: Record<string, string> = {
  bottom_reversal: "底部反转",
  trend_momentum: "趋势跟踪",
};

function MobileStockPool() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [items, setItems] = useState<Record<string, any>[]>([]);
  const [activeFilter, setActiveFilter] = useState("全部");
  const [detailCode, setDetailCode] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const parseScore = (s: string | null | undefined): number => {
    if (!s) return 0;
    const n = parseFloat(s);
    return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const transformItem = (item: Record<string, any>) => {
    const totalScore = parseScore(item.score_total);
    return {
      code: item.stock_code || "--",
      name: item.stock_name || item.stock_code?.replace(".SH","").replace(".SZ","") || "",
      strategy: STRATEGY_NAMES[item.strategy_type] || item.strategy_type || "未知",
      score: totalScore,
    };
  };

  useEffect(() => {
    let cancelled = false;

    strategyService
      .getPool()
      .then((data) => {
        if (!cancelled) {
          if (data && data.length > 0) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setItems(data.map((item: Record<string, any>) => transformItem(item)));
          } else {
            setItems([]);
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleRescan = useCallback(async () => {
    try {
      const result = await strategyService.scan();
      message.success(result.message || "扫描完成");
      // 自动刷新列表
      strategyService.getPool().then((data) => {
        if (data && data.length > 0) {
          setItems(data.map((item: Record<string, any>) => transformItem(item)));
        } else {
          setItems([]);
        }
      }).catch(() => {
        setItems([]);
      });
    } catch {
      message.error("扫描失败，请稍后重试");
    }
  }, [message]);

  const handleView = useCallback(
    (code: string) => {
      setDetailCode(code);
      setDetailOpen(true);
    },
    []
  );

  const filteredItems =
    activeFilter === "全部"
      ? items
      : items.filter((item) => item.strategy === activeFilter);

  const countTotal = items.length;
  const countNewToday = items.filter(
    (item) => item.changeUp === true || item.strategy === "周期底部"
  ).length;
  const newTodayLabel = countNewToday > 0 ? `${countNewToday} 今日新增` : "--";

  const avgScore =
    items.length > 0
      ? (items.reduce((sum, i) => sum + i.score, 0) / items.length).toFixed(1)
      : "0";

  if (loading) {
    return (
      <div className="page-enter"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 200,
        }}
      >
        <span style={{ color: colors.text.tertiary, fontSize: 14 }}>
          加载中...
        </span>
      </div>
    );
  }

  return (
    <div className="page-enter">
      {/* ===== 标题栏 ===== */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontSize: 18,
          fontWeight: 600,
          marginBottom: 14,
          lineHeight: 1.3,
        }}
      >
        <span style={{
          background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          股票池
        </span>
        <div style={{ marginLeft: "auto" }}>
          <button
            onClick={handleRescan}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "6px 14px",
              borderRadius: `${colors.radius.md}px`,
              fontSize: 13,
              fontWeight: 500,
              lineHeight: 1.4,
              cursor: "pointer",
              border: "none",
              outline: "none",
              background: colors.gradient.primary,
              color: colors.text.inverse,
              boxShadow: colors.btnShadow,
              transition: "all 0.15s ease",
            }}
          >
            重新扫描
          </button>
        </div>
      </div>

      {/* ===== 指标卡片 (2列) ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 14,
        }}
      >
        <MobileMetricCard
          label="池中数量"
          value={countTotal}
          change={{ text: newTodayLabel, type: "up" }}
        />
        <MobileMetricCard
          label="平均评分"
          value={avgScore}
          change={{ text: "+2.3", type: "up" }}
        />
      </div>

      {/* ===== 筛选状态栏 ===== */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 14,
          overflowX: "auto",
          scrollbarWidth: "none",
        }}
      >
        {STRATEGY_FILTERS.map((f) => (
          <span
            key={f}
            onClick={() => setActiveFilter(f)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              fontSize: 13,
              fontWeight: 500,
              lineHeight: 1.3,
              padding: "5px 14px",
              borderRadius: 20,
              cursor: "pointer",
              userSelect: "none",
              whiteSpace: "nowrap",
              background:
                activeFilter === f
                  ? colors.gradient.primary
                  : colors.bg.subtle,
              color:
                activeFilter === f
                  ? colors.text.inverse
                  : colors.text.secondary,
              border:
                activeFilter === f
                  ? "none"
                  : `1px solid ${colors.border.light}`,
              transition: "all 0.15s ease",
            }}
          >
            {f}
          </span>
        ))}
      </div>

      {/* ===== 候选股票表格 ===== */}
      <MobileSectionCard title={`候选股票 (${filteredItems.length})`}>
        <div style={{ overflowX: "auto", scrollbarWidth: "thin" }}>
          {/* 表头 */}
          <div
          style={{
            display: "flex",
            padding: "8px 14px",
            borderBottom: `1px solid ${colors.border.light}`,
            fontSize: 11,
            color: colors.text.tertiary,
            fontWeight: 500,
            gap: 6,
          }}
        >
          <span style={{ width: 80, flexShrink: 0 }}>代码</span>
          <span style={{ width: 85, flexShrink: 0 }}>名称</span>
          <span style={{ width: 55, flexShrink: 0 }}>策略</span>
          <span style={{ width: 50, flexShrink: 0, textAlign: "right" }}>
            评分
          </span>
          <span style={{ width: 50, flexShrink: 0, textAlign: "center" }}>
            操作
          </span>
        </div>{/* 表头结束 */}

        {/* 表体 */}
        {filteredItems.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "10px 14px",
                gap: 6,
                fontSize: 12,
                color: colors.text.primary,
                borderBottom:
                  idx < filteredItems.length - 1
                    ? `1px solid ${colors.border.light}`
                    : "none",
                whiteSpace: "nowrap",
              }}
            >
              <span
                style={{
                  width: 80,
                  flexShrink: 0,
                  fontWeight: 500,
                  fontSize: 13,
                }}
              >
                {item.code}
              </span>
              <span
                style={{
                  width: 85,
                  flexShrink: 0,
                  color: colors.text.secondary,
                }}
              >
                {item.name}
              </span>
              <span style={{ width: 55, flexShrink: 0 }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    fontSize: 10,
                    fontWeight: 500,
                    lineHeight: 1.3,
                    padding: "1px 6px",
                    borderRadius: 20,
                    backgroundColor:
                      item.strategy === "周期底部"
                        ? colors.semantic.amberBg
                        : colors.purple[50],
                    color:
                      item.strategy === "周期底部"
                        ? colors.semantic.amber
                        : colors.purple[500],
                  }}
                >
                  {item.strategy}
                </span>
              </span>
              <span
                style={{
                  width: 50,
                  flexShrink: 0,
                  textAlign: "right",
                  fontWeight: 600,
                  color: colors.purple[500],
                }}
              >
                {item.score.toFixed(1)}
              </span>
              <span
                style={{
                  width: 50,
                  flexShrink: 0,
                  textAlign: "center",
                }}
              >
                <button
                  onClick={() => handleView(item.code)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "3px 10px",
                    borderRadius: `${colors.radius.sm}px`,
                    fontSize: 11,
                    fontWeight: 500,
                    lineHeight: 1.3,
                    cursor: "pointer",
                    border: `1px solid ${colors.border.medium}`,
                    outline: "none",
                    background: "transparent",
                    color: colors.text.secondary,
                    transition: "all 0.15s ease",
                  }}
                >
                  查看
                </button>
              </span>
            </div>
          ))}
        </div>
      </MobileSectionCard>

      {/* 股票详情弹窗 */}
      <StockDetailDrawer
        code={detailCode || ""}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setDetailCode(null);
        }}
      />
    </div>
  );
}

export default MobileStockPool;
