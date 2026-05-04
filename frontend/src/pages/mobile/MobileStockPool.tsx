import { useCallback, useEffect, useRef, useState } from "react";
import { App, DatePicker } from "antd";
import dayjs from "dayjs";
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
  scan: "中证500",
};

function MobileStockPool() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  const [currentItems, setCurrentItems] = useState<StockPoolItem[]>([]);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [activeFilter, setActiveFilter] = useState("全部");
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [detailCode, setDetailCode] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const scanningRef = useRef(false);

  const parseScore = (s: string | null | undefined): number => {
    if (!s) return 0;
    const n = parseFloat(s);
    return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
  };

  /** 加载已选日期的股票池数据 */
  const fetchPoolByDate = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const data = await strategyService.getPool(date);
      setCurrentItems(data || []);
    } catch {
      setCurrentItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 刷新可用日期列表（从 stock_pool 拿到有数据的日期 + 保持选中） */
  const refreshAfterScan = useCallback(async (scannedDate: string) => {
    // 重新加载 stock_pool 数据
    const data = await strategyService.getPool();
    const allItems = data || [];
    const dates = Array.from(new Set(allItems.map((i) => i.date))).sort().reverse();
    setAvailableDates(dates);
    // 重新加载当前日期的数据
    await fetchPoolByDate(scannedDate);
    // 如果当前日期不在可用列表中，切到最新日期
    if (!dates.includes(scannedDate) && dates.length > 0) {
      setSelectedDate(dates[0]);
      await fetchPoolByDate(dates[0]);
    }
  }, [fetchPoolByDate]);

  /** 初始化：先加载 stock_pool 数据，再选中第一条 */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const data = await strategyService.getPool();
      if (cancelled) return;
      const allItems = data || [];
      const dates = Array.from(new Set(allItems.map((i) => i.date))).sort().reverse();
      setAvailableDates(dates);
      if (dates.length > 0) {
        setSelectedDate(dates[0]);
        await fetchPoolByDate(dates[0]);
      } else {
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /** 选择日期时重新请求 */
  const handleDateChange = useCallback((d: dayjs.Dayjs | null) => {
    if (!d) return;
    const dateStr = d.format("YYYY-MM-DD");
    setSelectedDate(dateStr);
    fetchPoolByDate(dateStr);
  }, [fetchPoolByDate]);

  /** 重新扫描：根据选中日期扫描 */
  const handleRescan = useCallback(async () => {
    if (!selectedDate) {
      message.warning("请先选择一个交易日");
      return;
    }
    if (scanningRef.current) return;
    scanningRef.current = true;
    setScanning(true);
    try {
      const result = await strategyService.scan(selectedDate);
      message.success(result.message || "扫描完成");
      // 刷新 stock_pool 日期列表 + 重新加载当前日期数据
      await refreshAfterScan(selectedDate);
    } catch (e) {
      console.error("扫描失败", e);
      message.error("扫描失败，请稍后重试");
    } finally {
      scanningRef.current = false;
      setScanning(false);
      setLoading(false);
    }
  }, [selectedDate, message, refreshAfterScan]);

  const handleView = useCallback((code: string) => {
    setDetailCode(code);
    setDetailOpen(true);
  }, []);

  const dateItems = currentItems;

  const filteredItems =
    activeFilter === "全部"
      ? dateItems
      : activeFilter === "底部反转"
        ? dateItems.filter((item) => BOTTOM_KEYS.has(item.strategy_type))
        : dateItems.filter((item) => STRATEGY_NAMES[item.strategy_type] === activeFilter);

  const countTotal = dateItems.length;
  const avgScore =
    dateItems.length > 0
      ? (dateItems.reduce((sum, i) => sum + parseScore(i.score_total), 0) / dateItems.length).toFixed(1)
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
              boxShadow: colors.btnShadow }}>
            {scanning ? "扫描中..." : `扫描 ${selectedDate || ""}`}
          </button>
        </div>
      </div>

      {/* ===== 概况卡片 ===== */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
        <MobileMetricCard label="池中数量" value={countTotal}
          change={{ text: selectedDate || "--", type: "up" }} />
        <MobileMetricCard label="平均评分" value={avgScore}
          change={{ text: "0-100", type: "up" }} />
      </div>

      {/* ===== 交易日选择：DatePicker ===== */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: colors.text.tertiary, marginBottom: 6 }}>
          选择交易日
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <DatePicker
            value={selectedDate ? dayjs(selectedDate) : null}
            onChange={handleDateChange}
            allowClear={false}
            size="small"
            style={{ width: 140, borderRadius: `${colors.radius.md}px` }}
            picker="date"
            inputReadOnly
          />
          <span style={{ fontSize: 11, color: colors.text.tertiary }}>
            {availableDates.length > 0
              ? `含 ${availableDates.length} 个交易日数据`
              : "选日期扫描后即生成"}
          </span>
        </div>
      </div>

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
        <div style={{ overflowX: "auto" }}>
          {/* 表头 */}
          <div style={{ display: "flex", padding: "8px 14px", borderBottom: `1px solid ${colors.border.light}`,
            fontSize: 11, color: colors.text.tertiary, fontWeight: 500, gap: 6 }}>
            <span style={{ width: 70, flexShrink: 0 }}>代码</span>
            <span style={{ flex: 1, minWidth: 60 }}>名称</span>
            <span style={{ width: 58, flexShrink: 0, textAlign: "center" }}>策略</span>
            <span style={{ width: 40, flexShrink: 0, textAlign: "right" }}>评分</span>
          </div>

          {/* 表体 */}
          {filteredItems.map((item, idx) => {
            const score = parseScore(item.score_total);
            const strategyName = STRATEGY_NAMES[item.strategy_type] || item.strategy_type || "未知";
            const shortCode = (item.stock_code || "").replace(".SH","").replace(".SZ","");
            return (
              <div key={idx}
                style={{ display: "flex", alignItems: "center", padding: "10px 14px", gap: 6,
                  fontSize: 12, color: colors.text.primary,
                  borderBottom: idx < filteredItems.length - 1 ? `1px solid ${colors.border.light}` : "none" }}>
                <span style={{ width: 70, flexShrink: 0, fontWeight: 600, fontSize: 12, fontFamily: "monospace", letterSpacing: "0.02em" }}>
                  {shortCode}
                </span>
                <span onClick={() => handleView(item.stock_code || "")}
                  style={{ flex: 1, minWidth: 60, color: colors.text.primary, fontWeight: 500,
                    cursor: "pointer", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.stock_name || shortCode}
                </span>
                <span style={{ width: 58, flexShrink: 0, textAlign: "center" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", fontSize: 10, fontWeight: 500,
                    lineHeight: 1.3, padding: "1px 6px", borderRadius: 20,
                    backgroundColor: strategyName === "底部反转" ? colors.semantic.amberBg : colors.purple[50],
                    color: strategyName === "底部反转" ? colors.semantic.amber : colors.purple[500] }}>
                    {strategyName}
                  </span>
                </span>
                <span style={{ width: 40, flexShrink: 0, textAlign: "right", fontWeight: 700, color: colors.purple[500], fontSize: 13 }}>
                  {score.toFixed(1)}
                </span>
              </div>
            );
          })}
          {filteredItems.length === 0 && (
            <div style={{ padding: "24px 14px", textAlign: "center", fontSize: 12, color: colors.text.tertiary }}>
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
