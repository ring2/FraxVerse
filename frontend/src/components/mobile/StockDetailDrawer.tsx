import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { marketService } from "../../services/marketService";
import {
  init as klineInit,
  dispose as klineDispose,
  type Chart,
} from "klinecharts";

/* ─── 类型 ─── */
interface KlineItem {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change_pct: number;
}

type PeriodTab = "1m" | "15m" | "30m" | "day" | "week" | "month";

interface Props {
  code: string;
  open: boolean;
  onClose: () => void;
}

/* ─── 周期映射 ─── */
const PERIOD_TABS: { key: PeriodTab; label: string }[] = [
  { key: "1m", label: "1分" },
  { key: "15m", label: "15分" },
  { key: "30m", label: "30分" },
  { key: "day", label: "日" },
  { key: "week", label: "周" },
  { key: "month", label: "月" },
];

/* ─── 深色K线面板样式（专业交易软件风格） ─── */
const DARK_STYLES = {
  grid: {
    horizontal: { color: "rgba(255,255,255,0.08)", style: "solid" as const, size: 0.5, show: true },
    vertical: { color: "transparent", show: false },
  },
  xAxis: {
    axisLine: { color: "rgba(255,255,255,0.15)" },
    tickText: { color: "rgba(255,255,255,0.55)", size: 10 },
  },
  yAxis: {
    axisLine: { color: "transparent" },
    tickText: { color: "rgba(255,255,255,0.55)", size: 10 },
  },
  candle: {
    bar: {
      upColor: "#EF5350",
      downColor: "#26A69A",
      upBorderColor: "#EF5350",
      downBorderColor: "#26A69A",
      upWickColor: "#EF5350",
      downWickColor: "#26A69A",
    },
    tooltip: {
      bgColor: "rgba(40,40,48,0.95)",
      color: "rgba(255,255,255,0.9)",
    },
  },
  crosshair: {
    line: { color: "rgba(255,255,255,0.2)", dashed: true },
    verticalText: { color: "rgba(255,255,255,0.6)", borderSize: 0 },
    horizontalText: { color: "rgba(255,255,255,0.6)", borderSize: 0 },
  },
};

/* ─── 工具函数 ─── */
const fmt = (v: number | null | undefined) => {
  if (v == null) return "--";
  return v.toFixed(2);
};
const fmtVolume = (v: number | null | undefined) => {
  if (!v) return "--";
  if (v >= 1e8) return (v / 1e8).toFixed(2) + "亿";
  if (v >= 1e4) return (v / 1e4).toFixed(2) + "万";
  return v.toFixed(0);
};
const fmtYi = (v: number | null | undefined) => {
  if (!v) return "--";
  return (v / 1e8).toFixed(2) + "亿";
};

/* ─── 主组件 ─── */
function StockDetailDrawer({ code, open, onClose }: Props) {
  const { colors: theme } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const chartId = `stock-kline-${code}`;

  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [visible, setVisible] = useState(false);
  const [animClass, setAnimClass] = useState("");
  const [activePeriod, setActivePeriod] = useState<PeriodTab>("day");
  const [klines, setKlines] = useState<KlineItem[]>([]);
  const [klinesLoading, setKlinesLoading] = useState(false);

  // 价格数据
  const price = detail ? Number((detail as Record<string, number>).price || 0) : 0;
  const changePct = detail ? Number((detail as Record<string, number>).change_pct || 0) : 0;
  const isUp = changePct >= 0;
  const changeColor = isUp ? "#F46666" : "#19AA5C";
  const name = (detail as Record<string, string>)?.name || code.replace(/\.(SH|SZ)$/, "");
  const stockCode = (detail as Record<string, string>)?.code || code;

  // 弹出/关闭动画
  useEffect(() => {
    if (open) {
      setVisible(true);
      requestAnimationFrame(() => setAnimClass("in"));
    } else {
      setAnimClass("out");
      const t = setTimeout(() => {
        setVisible(false);
        setDetail(null);
        setKlines([]);
        setActivePeriod("day");
      }, 280);
      return () => clearTimeout(t);
    }
  }, [open]);

  // 加载行情详情
  useEffect(() => {
    if (!open || !code) return;
    let cancelled = false;
    setLoading(true);
    marketService
      .getStockDetail(code)
      .then((data) => {
        if (cancelled) return;
        setDetail(data);
        setLoading(false);
        const k = (data as Record<string, KlineItem[]>)?.klines;
        if (k?.length) setKlines(k);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setLoading(false);
          App.useApp().message.error(`加载行情失败: ${err?.message || "未知错误"}`);
        }
      });
    return () => { cancelled = true; };
  }, [code, open]);

  // 切换周期时加载K线数据
  useEffect(() => {
    if (!open || !code) return;
    let cancelled = false;

    // 日K直接复用 stock-detail 返回的数据
    if (activePeriod === "day" && klines.length > 0) return;

    const periodMap: Record<PeriodTab, string> = {
      "1m": "1", "15m": "15", "30m": "30",
      day: "daily", week: "weekly", month: "monthly",
    };
    const limitMap: Record<PeriodTab, number> = {
      "1m": 120, "15m": 120, "30m": 120,
      day: 120, week: 120, month: 60,
    };

    setKlinesLoading(true);
    marketService
      .getKlines({ code, period: periodMap[activePeriod], limit: limitMap[activePeriod] })
      .then((data) => {
        if (cancelled) return;
        const mapped: KlineItem[] = (data || []).map((k: Record<string, unknown>) => ({
          trade_date: String((k as { timestamp?: string; trade_date?: string }).timestamp ?? ""),
          open: Number(k.open ?? 0),
          high: Number(k.high ?? 0),
          low: Number(k.low ?? 0),
          close: Number(k.close ?? 0),
          volume: Number(k.volume ?? 0),
          change_pct: Number(k.change_pct ?? 0),
        }));
        setKlines(mapped);
        setKlinesLoading(false);
      })
      .catch(() => { if (!cancelled) setKlinesLoading(false); });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePeriod, code, open]);

  // 渲染K线图表
  useEffect(() => {
    if (!visible || klines.length === 0) return;

    const existing = document.getElementById(chartId);
    if (!existing) return;
    const parent = existing.parentElement;
    if (parent) parent.style.height = "340px";

    try { klineDispose(chartId); } catch { /* ignore */ }

    // 等DOM动画一帧后再初始化，确保容器尺寸已就绪
    const raf = requestAnimationFrame(() => {
      const chart = klineInit(chartId, {
        styles: DARK_STYLES as Record<string, unknown>,
      });
      if (!chart) return;
      chartInstance.current = chart;

      chart.setSymbol({ ticker: code, name });
      // 设置周期，确保 dataLoader 被触发
      chart.setPeriod({ type: "day", span: 1 });

      const bars = klines.map((k) => ({
        timestamp: new Date(k.trade_date).getTime(),
        open: k.open, high: k.high, low: k.low, close: k.close, volume: k.volume,
      }));

      // 注入颜色样式（在 init 的 styles 参数之后额外应用一次，确保生效）
      try { (chart as any).setStyles(DARK_STYLES); } catch { /* ignore */ }

      // 注入数据
      try {
        chart.setDataLoader({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          getBars: (params: any) => {
            params.callback(bars, { backward: false, forward: false });
          },
        });
        // 强制触发数据加载
        setTimeout(() => {
          try { (chart as any).resize(); } catch { /* ignore */ }
        }, 50);
      } catch { /* ignore */ }

      // 调试角标
      try {
        const debugEl = document.getElementById(chartId);
        if (debugEl) {
          const badge = document.createElement("div");
          badge.style.cssText = "position:absolute;top:4px;right:4px;background:#1A1A2E;color:#26A69A;font-size:10px;padding:2px 6px;border-radius:4px;z-index:10;font-family:monospace;";
          badge.textContent = `📊 ${bars.length} bars`;
          const parent = debugEl.parentElement;
          if (parent) parent.style.position = "relative";
          parent?.appendChild(badge);
        }
      } catch { /* ignore */ }

      try { chart.createIndicator("VOL", false, { id: "candle_pane" }); } catch { /* ignore */ }
      try { chart.createIndicator("MA", false, { id: "candle_pane" }); } catch { /* ignore */ }
    });

    return () => {
      cancelAnimationFrame(raf);
      try { klineDispose(chartId); } catch { /* ignore */ }
      chartInstance.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, klines, code, name]);

  // 行情指标数据
  const infoCards = [
    { label: "最高", value: fmt((detail as Record<string, number>)?.high), color: "#F46666" },
    { label: "最低", value: fmt((detail as Record<string, number>)?.low), color: "#19AA5C" },
    { label: "今开", value: fmt((detail as Record<string, number>)?.open) },
    { label: "昨收", value: fmt((detail as Record<string, number>)?.pre_close) },
    { label: "量比", value: (detail as Record<string, number>)?.volume_ratio ? Number((detail as Record<string, number>).volume_ratio).toFixed(2) : "--" },
    { label: "换手率", value: (detail as Record<string, number>)?.turnover_rate ? `${Number((detail as Record<string, number>).turnover_rate).toFixed(2)}%` : "--" },
    { label: "市盈率", value: (detail as Record<string, number>)?.pe ? Number((detail as Record<string, number>).pe).toFixed(2) : "--" },
    { label: "市净率", value: (detail as Record<string, number>)?.pb ? Number((detail as Record<string, number>).pb).toFixed(2) : "--" },
    { label: "成交量", value: fmtVolume((detail as Record<string, number>)?.volume) },
    { label: "成交额", value: fmtVolume((detail as Record<string, number>)?.amount) },
    { label: "总市值", value: fmtYi((detail as Record<string, number>)?.total_value) },
    { label: "流通市值", value: fmtYi((detail as Record<string, number>)?.circulate_value) },
  ];

  if (!visible) return null;

  const drawerContent = (
    <div style={{ position: "fixed", inset: 0, zIndex: 9999, touchAction: "none" }}>
      {/* 遮罩 */}
      <div onClick={onClose} style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.35)",
        opacity: animClass === "in" ? 1 : 0,
        transition: "opacity 0.28s ease",
      }} />

      {/* 面板 — 使用主题背景色100%覆盖 */}
      <div style={{
        position: "fixed", bottom: 0, left: 0, right: 0, top: 0,
        background: theme.bg.page,
        overflow: "hidden",
        display: "flex", flexDirection: "column",
        transform: animClass === "in" ? "translateY(0)" : "translateY(100%)",
        opacity: animClass === "in" ? 1 : 0,
        transition: "transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.3s ease",
      }}>

        {/* ═══ 头部导航 ═══ */}
        <div style={{
          display: "flex", alignItems: "center",
          padding: "12px 16px 0", flexShrink: 0,
          borderBottom: `1px solid ${theme.border.light}`,
          paddingBottom: 10,
        }}>
          <button onClick={onClose} style={{
            background: "none", border: "none",
            color: theme.text.secondary, fontSize: 20,
            padding: 0, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 4,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>

          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, marginLeft: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: theme.text.primary }}>{name}</span>
            <span style={{ fontSize: 11, color: theme.text.tertiary, fontFamily: "monospace" }}>{stockCode}</span>
          </div>

          {/* 价格 */}
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: changeColor, fontFamily: "monospace", lineHeight: 1 }}>
              {price > 0 ? price.toFixed(2) : "--"}
            </span>
            <span style={{
              fontSize: 12, fontWeight: 600, color: "#fff",
              background: changeColor, padding: "1px 6px", borderRadius: 4,
            }}>
              {changePct > 0 ? "+" : ""}{changePct.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* ═══ 周期切换栏 ═══ */}
        <div style={{
          display: "flex", gap: 2, padding: "10px 16px 8px",
          flexShrink: 0, overflowX: "auto",
          WebkitOverflowScrolling: "touch",
          borderBottom: `1px solid ${theme.border.light}`,
        }}>
          {PERIOD_TABS.map((tab) => (
            <button key={tab.key} onClick={() => { setActivePeriod(tab.key); setKlines([]); }}
              style={{
                flexShrink: 0, padding: "3px 11px", fontSize: 12,
                fontWeight: activePeriod === tab.key ? 600 : 400,
                color: activePeriod === tab.key ? theme.text.primary : theme.text.tertiary,
                background: activePeriod === tab.key ? theme.bg.surface : "transparent",
                border: "1px solid",
                borderColor: activePeriod === tab.key ? theme.border.medium : "transparent",
                borderRadius: 6, cursor: "pointer", transition: "all 0.15s ease",
              }}
            >
              {tab.label}
            </button>
          ))}
          {klinesLoading && <span style={{ marginLeft: "auto", fontSize: 11, color: theme.text.tertiary, display: "flex", alignItems: "center" }}>加载中...</span>}
        </div>

        {/* ═══ K线区 ═══ */}
        <div data-kline-section style={{ flexShrink: 0, padding: "8px 12px", position: "relative" }}>
          <div style={{
            background: theme.bg.surface,
            borderRadius: 10, padding: 4,
            border: `1px solid ${theme.border.light}`,
          }}>
            <div id={chartId} ref={chartRef} style={{ width: "100%", height: 320, borderRadius: 8, background: "#1A1A2E" }} />
            {klines.length === 0 && !klinesLoading && (
              <div style={{
                position: "absolute", inset: 0, display: "flex",
                alignItems: "center", justifyContent: "center",
                color: theme.text.tertiary, fontSize: 13,
              }}>
                {loading ? "加载数据..." : "暂无K线数据"}
              </div>
            )}
          </div>
        </div>

        {/* ═══ 可滚动信息区 ═══ */}
        <div style={{
          flex: 1, overflowY: "auto", WebkitOverflowScrolling: "touch",
          padding: "0 16px 24px",
        }}>
          {loading && !detail && (
            <div style={{ padding: "40px 0", textAlign: "center", color: theme.text.tertiary, fontSize: 13 }}>
              加载行情...
            </div>
          )}

          {detail && (
            <>
              {/* 价格 & 涨跌 */}
              <div style={{ display: "flex", gap: 8, marginBottom: 12, marginTop: 12 }}>
                <div style={{
                  flex: 1, background: theme.bg.surface, borderRadius: 10,
                  padding: "14px 16px", border: `1px solid ${theme.border.light}`,
                }}>
                  <div style={{ fontSize: 11, color: theme.text.tertiary, marginBottom: 4 }}>当前价格</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: changeColor, fontFamily: "monospace", lineHeight: 1.1 }}>
                    {price > 0 ? price.toFixed(2) : "--"}
                  </div>
                </div>
                <div style={{
                  flex: 1, background: theme.bg.surface, borderRadius: 10,
                  padding: "14px 16px", border: `1px solid ${theme.border.light}`,
                }}>
                  <div style={{ fontSize: 11, color: theme.text.tertiary, marginBottom: 4 }}>涨跌幅</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: changeColor, fontFamily: "monospace", lineHeight: 1.1 }}>
                    {changePct > 0 ? "+" : ""}{changePct.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: 12, color: theme.text.tertiary, marginTop: 2 }}>
                    昨收 {fmt((detail as Record<string, number>).pre_close)}
                  </div>
                </div>
              </div>

              {/* 指标网格 3列 */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6, marginBottom: 16 }}>
                {infoCards.map((item) => (
                  <div key={item.label} style={{
                    background: theme.bg.surface, padding: "10px 12px",
                    borderRadius: 8, border: `1px solid ${theme.border.light}`,
                  }}>
                    <div style={{ fontSize: 10, color: theme.text.tertiary, fontWeight: 500, marginBottom: 3 }}>{item.label}</div>
                    <div style={{
                      fontSize: 14, fontWeight: 600,
                      color: item.color || theme.text.primary,
                      fontFamily: "monospace",
                    }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(drawerContent, document.body);
}

export default StockDetailDrawer;
