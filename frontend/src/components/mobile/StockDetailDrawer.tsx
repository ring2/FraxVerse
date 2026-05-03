import { useEffect, useRef, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import { marketService } from "../../services/marketService";
import { init, dispose } from "klinecharts";

interface Props {
  code: string;
  open: boolean;
  onClose: () => void;
}

function StockDetailDrawer({ code, open, onClose }: Props) {
  const { message } = App.useApp();
  const { colors } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [detail, setDetail] = useState<Record<string, any> | null>(null);

  const price = detail ? Number(detail.price || 0) : 0;
  const changePct = detail ? Number(detail.change_pct || 0) : 0;
  const isUp = changePct >= 0;
  const changeColor = isUp ? "#F46666" : "#1EAB5C";

  useEffect(() => {
    if (!open || !code) return;
    let cancelled = false;
    setLoading(true);

    marketService
      .getStockDetail(code)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          message.error(`加载行情失败: ${err?.message || "未知错误"}`);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [code, open, message]);

  // klinecharts 渲染
  useEffect(() => {
    if (!open || !chartRef.current || !detail?.klines) return;
    const klines = detail.klines as Array<{
      trade_date: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>;
    if (!klines.length) return;

    const chartId = "stock-kline-chart";
    const chart = init(chartId);
    if (!chart) return;

    // 设置样式（深色适配轻薄风格）
    chart.setStyles({
      grid: { horizontal: { color: "#2a2a2e" }, vertical: { color: "transparent" } },
      xAxis: {
        axisLine: { color: "#3a3a3e" },
        tickText: { color: "#888" },
      },
      yAxis: {
        axisLine: { color: "transparent" },
        tickText: { color: "#888" },
      },
      candle: {
        bar: {
          upColor: "#F46666",
          downColor: "#1EAB5C",
          upBorderColor: "#F46666",
          downBorderColor: "#1EAB5C",
        },
      },
      separator: { color: "transparent" },
    });

    // 设置数据
    chart.setSymbol({ ticker: code });
    chart.setPeriod({ span: 1, type: "day" });

    chart.setDataLoader({
      getBars: ({ callback }) => {
        const bars = klines.map((k) => ({
          timestamp: new Date(k.trade_date).getTime(),
          open: k.open,
          high: k.high,
          low: k.low,
          close: k.close,
          volume: k.volume,
        }));
        callback(bars);
      },
    });

    return () => {
      dispose(chartId);
    };
  }, [open, detail, code]);

  if (!open) return null;

  const fmt = (v: number | null | undefined) => {
    if (v == null || v === undefined) return "--";
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

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: colors.bg.page,
        overflowY: "auto",
        WebkitOverflowScrolling: "touch",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* 顶部导航栏 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: `1px solid ${colors.border.light}`,
          flexShrink: 0,
        }}
      >
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            fontSize: 20,
            color: colors.text.primary,
            cursor: "pointer",
            padding: "0 8px 0 0",
            lineHeight: 1,
          }}
        >
          ←
        </button>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 17, fontWeight: 600, color: colors.text.primary }}>
            {detail?.name || code}
          </span>
          <span style={{ fontSize: 12, color: colors.text.tertiary, marginLeft: 8 }}>
            {detail?.code || code}
          </span>
        </div>
        {loading && (
          <span style={{ fontSize: 12, color: colors.text.tertiary }}>加载中...</span>
        )}
      </div>

      {/* 加载失败 / 无数据 */}
      {!detail && !loading && (
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: colors.text.tertiary,
            fontSize: 14,
          }}
        >
          暂无行情数据
        </div>
      )}

      {detail && (
        <>
          {/* 价格区域 */}
          <div style={{ padding: "20px 16px 16px", flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <span style={{ fontSize: 32, fontWeight: 700, color: changeColor }}>
                {price > 0 ? price.toFixed(2) : "--"}
              </span>
              <span
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: changeColor,
                  background: isUp ? "rgba(244,102,102,0.1)" : "rgba(30,171,92,0.1)",
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                {changePct > 0 ? "+" : ""}
                {changePct.toFixed(2)}%
              </span>
              <span style={{ fontSize: 12, color: colors.text.tertiary }}>
                昨收 {fmt(detail.pre_close)}
              </span>
            </div>
          </div>

          {/* 行情卡片 Grid — 2列布局更适手机 */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
              margin: "0 16px 16px",
              flexShrink: 0,
            }}
          >
            {[
              { label: "最高", value: fmt(detail.high) },
              { label: "最低", value: fmt(detail.low) },
              { label: "今开", value: fmt(detail.open) },
              { label: "昨收", value: fmt(detail.pre_close) },
              { label: "量比", value: detail.volume_ratio ? detail.volume_ratio.toFixed(2) : "--" },
              { label: "换手率", value: detail.turnover_rate ? detail.turnover_rate.toFixed(2) + "%" : "--" },
              { label: "市盈率", value: detail.pe ? detail.pe.toFixed(2) : "--" },
              { label: "市净率", value: detail.pb ? detail.pb.toFixed(2) : "--" },
              { label: "成交量", value: fmtVolume(detail.volume) },
              { label: "成交额", value: fmtVolume(detail.amount) },
              { label: "总市值", value: fmtYi(detail.total_value) },
              { label: "流通市值", value: fmtYi(detail.circulate_value) },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  background: colors.bg.surface,
                  padding: "10px 10px",
                  borderRadius: 8,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ fontSize: 12, color: colors.text.tertiary }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>

          {/* K线区域 */}
          <div style={{ flex: 1, padding: "0 16px 20px", minHeight: 300 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: colors.text.primary,
                marginBottom: 8,
              }}
            >
              日K线
            </div>
            <div
              id="stock-kline-chart"
              ref={chartRef}
              style={{
                width: "100%",
                height: 320,
                borderRadius: 8,
                background: colors.bg.surface,
              }}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default StockDetailDrawer;
