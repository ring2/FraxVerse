import { useCallback, useEffect, useMemo, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
  StockDetailDrawer,
} from "../../components/mobile";
import { strategyService } from "../../services/strategyService";
import type { StockPoolItem } from "../../types/api-extended";

const STRATEGY_FILTERS = ["全部", "底部反转", "趋势跟踪"];
const BOTTOM_KEYS = new Set(["bottom_reversal", "bottom_volume"]);

const STRATEGY_NAMES: Record<string, string> = {
  bottom_reversal: "底部反转",
  trend_momentum: "趋势跟踪",
  bottom_volume: "底部反转",
};

/** 获取所有可用的交易日（从数据中提取） */
function extractDates(items: StockPoolItem[]): string[] {
  const set = new Set<string>();
  for (const item of items) {
    if (item.date) set.add(item.date);
  }
  return Array.from(set).sort().reverse(); // 最新的在前
}

function MobileStockPool() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<StockPoolItem[]>([]);
  const [activeFilter, setActiveFilter] = useState("全部");
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [detailCode, setDetailCode] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const parseScore = (s: string | null | undefined): number => {
    if (!s) return 0;
    const n = parseFloat(s);
    return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
  };

  /** 带日期参数的加载 */
  const loadPool = useCallback(async (poolDate?: string) => {
    try {
      const data = await strategyService.getPool(poolDate);
      setItems(data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 首次加载：先查最新的（不传参数），再设 selectedDate */
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    strategyService.getPool().then((data) => {
      if (cancelled) return;
      const pool = data || [];
      setItems(pool);
      // 如果有数据，自动选中最新日期
      const dates = extractDates(pool);
      if (dates.length > 0) {
        setSelectedDate(dates[0]);
      }
    }).catch(() => {
      if (!cancelled) setItems([]);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  /** 切换日期时重新查询 */
  const handleDateChange = useCallback((date: string) => {
    setSelectedDate(date);
    setLoading(true);
    loadPool(date);
  }, [loadPool]);

  const handleRescan = useCallback(async () => {
    try {
      const result = await strategyService.scan();
      message.success(result.message || "扫描完成");
      // 重新加载最新数据
      setLoading(true);
      strategyService.getPool().then((data) => {
        const pool = data || [];
        setItems(pool);
        const dates = extractDates(pool);
        if (dates.length > 0) setSelectedDate(dates[0]);
      }).catch(() => {
        setItems([]);
      }).finally(() => {
        setLoading(false);
      });
    } catch {
      message.error("扫描失败，请稍后重试");
    }
  }, [message]);

  const handleView = useCallback((code: string) => {
    setDetailCode(code);
    setDetailOpen(true);
  }, []);

  const availableDates = useMemo(() => extractDates(items), [items]);
  const latestDate = availableDates.length > 0 ? availableDates[0] : "--";
  // 当前选中的日期的数据（用于筛选）
  const dateFilteredItems = selectedDate
    ? items.filter((i) => i.date === selectedDate)
    : items;

  const filteredItems =
    activeFilter === "全部"
      ? dateFilteredItems
      : activeFilter === "底部反转"
        ? dateFilteredItems.filter((item) => BOTTOM_KEYS.has(item.strategy_type))
        : dateFilteredItems.filter((item) => STRATEGY_NAMES[item.strategy_type] === activeFilter);

  const countTotal = dateFilteredItems.length;
  const avgScore =
    dateFilteredItems.length > 0
      ? (dateFilteredItems.reduce((sum, i) => sum + parseScore(i.score_total), 0) / dateFilteredItems.length).toFixed(1)
      : "0";

  if (loading) {
    return (
      <div className="page-enter"
        style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 200 }}>
        <span style={{ color: colors.text.tertiary, fontSize: 14 }}>加载中...</span>
      </div>
    );
  }

  return (
    <div className="page-enter">
      {/* ===== 标题栏 ===== */}
      <div style={{ display: "flex", alignItems: "center", fontSize: 18, fontWeight: 600, marginBottom: 14, lineHeight: 1.3 }}>
        <span style={{
          background: "linear-gradient(135deg, #7F77DD, #9B93E4)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
        }}>
          股票池
        </span>
        <div style={{ marginLeft: "auto" }}>
          <button onClick={handleRescan}
            style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "6px 14px",
              borderRadius: `${colors.radius.md}px`, fontSize: 13, fontWeight: 500, lineHeight: 1.4,
              cursor: "pointer", border: "none", outline: "none",
              background: colors.gradient.primary, color: colors.text.inverse,
              boxShadow: colors.btnShadow, transition: "all 0.15s ease" }}>
            重新扫描
          </button>
        </div>
      </div>

      {/* ===== 指标卡片 (2列) ===== */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
        <MobileMetricCard label="池中数量" value={countTotal}
          change={{ text: selectedDate ? selectedDate : latestDate, type: "up" }} />
        <MobileMetricCard label="平均评分" value={avgScore}
          change={{ text: "评分制 0-100", type: "up" }} />
      </div>

      {/* ===== 日期选择器 ===== */}
      {availableDates.length > 0 && (
        <div style={{ display: "flex", gap: 6, marginBottom: 10, overflowX: "auto", scrollbarWidth: "none" }}>
          {availableDates.map((d) => (
            <span key={d} onClick={() => handleDateChange(d)}
              style={{ display: "inline-flex", alignItems: "center", fontSize: 12, fontWeight: 500,
                lineHeight: 1.3, padding: "4px 12px", borderRadius: 20, cursor: "pointer",
                userSelect: "none", whiteSpace: "nowrap", flexShrink: 0,
                background: selectedDate === d ? colors.gradient.primary : colors.bg.subtle,
                color: selectedDate === d ? colors.text.inverse : colors.text.secondary,
                border: selectedDate === d ? "none" : `1px solid ${colors.border.light}`,
                transition: "all 0.15s ease" }}>
              {d}
            </span>
          ))}
        </div>
      )}

      {/* ===== 策略筛选 ===== */}
      <div style={{ display: "flex", gap: 8, marginBottom: 14, overflowX: "auto", scrollbarWidth: "none" }}>
        {STRATEGY_FILTERS.map((f) => (
          <span key={f} onClick={() => setActiveFilter(f)}
            style={{ display: "inline-flex", alignItems: "center", fontSize: 13, fontWeight: 500,
              lineHeight: 1.3, padding: "5px 14px", borderRadius: 20, cursor: "pointer",
              userSelect: "none", whiteSpace: "nowrap",
              background: activeFilter === f ? colors.gradient.primary : colors.bg.subtle,
              color: activeFilter === f ? colors.text.inverse : colors.text.secondary,
              border: activeFilter === f ? "none" : `1px solid ${colors.border.light}`,
              transition: "all 0.15s ease" }}>
            {f}
          </span>
        ))}
      </div>

      {/* ===== 候选股票表格 ===== */}
      <MobileSectionCard title={`候选股票 (${filteredItems.length})`}>
        <div style={{ overflowX: "auto", scrollbarWidth: "thin" }}>
          {/* 表头 */}
          <div style={{ display: "flex", padding: "8px 14px", borderBottom: `1px solid ${colors.border.light}`,
            fontSize: 11, color: colors.text.tertiary, fontWeight: 500, gap: 6 }}>
            <span style={{ width: 75, flexShrink: 0 }}>代码</span>
            <span style={{ width: 90, flexShrink: 0 }}>名称</span>
            <span style={{ width: 60, flexShrink: 0 }}>策略</span>
            <span style={{ width: 50, flexShrink: 0, textAlign: "right" }}>评分</span>
          </div>

          {/* 表体 */}
          {filteredItems.map((item, idx) => {
            const score = parseScore(item.score_total);
            const strategyName = STRATEGY_NAMES[item.strategy_type] || item.strategy_type || "未知";
            return (
              <div key={idx}
                style={{ display: "flex", alignItems: "center", padding: "10px 14px", gap: 6,
                  fontSize: 12, color: colors.text.primary,
                  borderBottom: idx < filteredItems.length - 1 ? `1px solid ${colors.border.light}` : "none",
                  whiteSpace: "nowrap" }}>
                <span style={{ width: 75, flexShrink: 0, fontWeight: 500, fontSize: 13 }}>
                  {item.stock_code || "--"}
                </span>
                <span onClick={() => handleView(item.stock_code || "")}
                  style={{ width: 90, flexShrink: 0, color: colors.text.primary, fontWeight: 500,
                    cursor: "pointer", textDecoration: "underline", textDecorationColor: colors.text.tertiary,
                    textUnderlineOffset: 2 }}>
                  {item.stock_name || item.stock_code?.replace(".SH","").replace(".SZ","") || ""}
                </span>
                <span style={{ width: 60, flexShrink: 0 }}>
                  <span style={{ display: "inline-flex", alignItems: "center", fontSize: 10, fontWeight: 500,
                    lineHeight: 1.3, padding: "1px 6px", borderRadius: 20,
                    backgroundColor: strategyName === "底部反转" ? colors.semantic.amberBg : colors.purple[50],
                    color: strategyName === "底部反转" ? colors.semantic.amber : colors.purple[500] }}>
                    {strategyName}
                  </span>
                </span>
                <span style={{ width: 50, flexShrink: 0, textAlign: "right", fontWeight: 600, color: colors.purple[500] }}>
                  {score.toFixed(1)}
                </span>
              </div>
            );
          })}
          {filteredItems.length === 0 && (
            <div style={{ padding: "20px 14px", textAlign: "center", fontSize: 12, color: colors.text.tertiary }}>
              {selectedDate ? `${selectedDate} 无候选股票` : "暂无数据"}
            </div>
          )}
        </div>
      </MobileSectionCard>

      {/* 股票详情弹窗 */}
      <StockDetailDrawer
        code={detailCode || ""}
        open={detailOpen}
        onClose={() => { setDetailOpen(false); setDetailCode(null); }}
      />
    </div>
  );
}

export default MobileStockPool;
