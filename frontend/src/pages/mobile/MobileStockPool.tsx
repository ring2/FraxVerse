import { useCallback, useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
} from "../../components/mobile";
import { strategyService } from "../../services/strategyService";

/* ---- Mock fallback data ---- */
const MOCK_POOL = [
  {
    code: "600519",
    name: "贵州茅台",
    strategy: "周期底部",
    score: 92,
    metrics: { liangjia: 88, zijin: 95, qingxu: 85, zhuli: 96 },
    change: "+3.2%",
    changeUp: true,
  },
  {
    code: "300750",
    name: "宁德时代",
    strategy: "趋势低吸",
    score: 87,
    metrics: { liangjia: 82, zijin: 90, qingxu: 80, zhuli: 92 },
    change: "+2.1%",
    changeUp: true,
  },
  {
    code: "000858",
    name: "五粮液",
    strategy: "周期底部",
    score: 74,
    metrics: { liangjia: 70, zijin: 78, qingxu: 72, zhuli: 76 },
    change: "+1.5%",
    changeUp: true,
  },
  {
    code: "601318",
    name: "中国平安",
    strategy: "趋势低吸",
    score: 68,
    metrics: { liangjia: 62, zijin: 72, qingxu: 65, zhuli: 70 },
    change: "-0.8%",
    changeUp: false,
  },
  {
    code: "002475",
    name: "立讯精密",
    strategy: "周期底部",
    score: 55,
    metrics: { liangjia: 50, zijin: 58, qingxu: 52, zhuli: 60 },
    change: "-1.2%",
    changeUp: false,
  },
];

const STRATEGY_FILTERS = ["全部", "周期底部", "趋势低吸"];

function MobileStockPool() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [items, setItems] = useState<Record<string, any>[]>([]);
  const [activeFilter, setActiveFilter] = useState("全部");

  useEffect(() => {
    let cancelled = false;

    strategyService
      .getPool()
      .then((data) => {
        if (!cancelled) {
          // Transform API data into display format if needed
          if (data && data.length > 0) {
            setItems(
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              data.map((item: Record<string, any>) => ({
                code: item.stock_code || "--",
                name: item.stock_name || "",
                strategy: item.strategy_type || "未知",
                score: item.score_total ? parseInt(item.score_total) : 0,
                metrics: {
                  liangjia: 80,
                  zijin: 80,
                  qingxu: 80,
                  zhuli: 80,
                },
                change: item.final_decision === "buy" ? "+0.0%" : "-0.0%",
                changeUp: item.final_decision === "buy",
              }))
            );
          } else {
            setItems(MOCK_POOL);
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems(MOCK_POOL);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleRescan = useCallback(() => {
    message.info("重新扫描 — 开发中");
  }, [message]);

  const handleView = useCallback(
    (code: string) => {
      message.info(`查看 ${code} 详情 — 开发中`);
    },
    [message]
  );

  const filteredItems =
    activeFilter === "全部"
      ? items
      : items.filter((item) => item.strategy === activeFilter);

  const countTotal = items.length;
  const countNewToday = 3;

  const avgScore =
    items.length > 0
      ? (items.reduce((sum, i) => sum + i.score, 0) / items.length).toFixed(1)
      : "78.5";

  if (loading) {
    return (
      <div
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
    <div>
      {/* ===== 标题栏 ===== */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontSize: 18,
          fontWeight: 600,
          color: colors.text.primary,
          marginBottom: 14,
          lineHeight: 1.3,
        }}
      >
        股票池
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
          change={{ text: `+${countNewToday} 今日新增`, type: "up" }}
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
          <span style={{ width: 70, flexShrink: 0 }}>名称</span>
          <span style={{ width: 70, flexShrink: 0 }}>策略</span>
          <span style={{ width: 50, flexShrink: 0, textAlign: "right" }}>
            评分
          </span>
          <span style={{ width: 40, flexShrink: 0, textAlign: "right" }}>
            量价
          </span>
          <span style={{ width: 40, flexShrink: 0, textAlign: "right" }}>
            资金
          </span>
          <span style={{ width: 40, flexShrink: 0, textAlign: "right" }}>
            情绪
          </span>
          <span style={{ width: 40, flexShrink: 0, textAlign: "right" }}>
            主力
          </span>
          <span style={{ width: 55, flexShrink: 0, textAlign: "right" }}>
            涨跌
          </span>
          <span style={{ width: 50, flexShrink: 0, textAlign: "center" }}>
            操作
          </span>
        </div>

        {/* 表体 — 支持横向滚动 */}
        <div style={{ overflowX: "auto", scrollbarWidth: "thin" }}>
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
                  width: 70,
                  flexShrink: 0,
                  color: colors.text.secondary,
                }}
              >
                {item.name}
              </span>
              <span style={{ width: 70, flexShrink: 0 }}>
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
                {item.score}
              </span>
              <span
                style={{
                  width: 40,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {item.metrics.liangjia}
              </span>
              <span
                style={{
                  width: 40,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {item.metrics.zijin}
              </span>
              <span
                style={{
                  width: 40,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {item.metrics.qingxu}
              </span>
              <span
                style={{
                  width: 40,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {item.metrics.zhuli}
              </span>
              <span
                style={{
                  width: 55,
                  flexShrink: 0,
                  textAlign: "right",
                  fontWeight: 500,
                  color: item.changeUp
                    ? colors.semantic.up
                    : colors.semantic.down,
                }}
              >
                {item.change}
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
    </div>
  );
}

export default MobileStockPool;
