import { useCallback, useEffect, useState } from "react";
import { App } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
} from "../../components/mobile";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";

/* ---- Mock fallback data ---- */
const MOCK_POSITIONS = [
  {
    stock_code: "600519",
    stock_name: "贵州茅台",
    total_volume: 200,
    cost_price: "1,552.30",
    current_price: "1,680.50",
    market_value: "336,100",
    unrealized_pnl_pct: "8.2",
    unrealized_pnl: "25,640",
  },
  {
    stock_code: "300750",
    stock_name: "宁德时代",
    total_volume: 500,
    cost_price: "223.00",
    current_price: "218.30",
    market_value: "109,150",
    unrealized_pnl_pct: "-2.1",
    unrealized_pnl: "-2,350",
  },
  {
    stock_code: "000858",
    stock_name: "五粮液",
    total_volume: 300,
    cost_price: "151.40",
    current_price: "156.80",
    market_value: "47,040",
    unrealized_pnl_pct: "3.5",
    unrealized_pnl: "1,620",
  },
];

const MOCK_ORDERS = [
  {
    id: "ord_001",
    stock_code: "600519",
    direction: "buy",
    order_type: "限价",
    price: "1,670.00",
    volume: 100,
    filled_volume: 100,
    status: "filled",
    created_at: "09:32",
  },
  {
    id: "ord_002",
    stock_code: "300750",
    direction: "sell",
    order_type: "市价",
    price: "-",
    volume: 200,
    filled_volume: 200,
    status: "filled",
    created_at: "10:15",
  },
];

const MOCK_PORTFOLIO = {
  total_market_value: 985420,
  total_pnl: 32180,
  total_pnl_pct: 3.38,
  available_cash: 298930,
  total_position_pct: 76.7,
};

function MobileTrade() {
  const { message } = App.useApp();
  const { colors } = useTheme();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [positions, setPositions] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [orders, setOrders] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [portfolio, setPortfolio] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      portfolioService.getPositions().catch(() => MOCK_POSITIONS),
      tradeService.getOrders().catch(() => MOCK_ORDERS),
      portfolioService.getSummary().catch(() => MOCK_PORTFOLIO),
    ])
      .then(([p, o, s]) => {
        if (cancelled) return;
        setPositions(p && p.length > 0 ? p : MOCK_POSITIONS);
        setOrders(o && o.length > 0 ? o : MOCK_ORDERS);
        setPortfolio(s || MOCK_PORTFOLIO);
      })
      .catch(() => {
        if (!cancelled) {
          setPositions(MOCK_POSITIONS);
          setOrders(MOCK_ORDERS);
          setPortfolio(MOCK_PORTFOLIO);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleStopLoss = useCallback(
    (code: string) => {
      message.info(`止损 ${code} — 开发中`);
    },
    [message]
  );

  const handleManualTrade = useCallback(() => {
    message.info("手动下单 — 开发中");
  }, [message]);

  const portfolioValue = portfolio?.total_market_value ?? 985420;
  const portfolioPnl = portfolio?.total_pnl ?? 32180;
  const portfolioPnlPct = portfolio?.total_pnl_pct ?? 3.38;
  const availableCash = portfolio?.available_cash ?? 298930;
  const positionPct = portfolio?.total_position_pct ?? 76.7;

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
        交易
        <div style={{ marginLeft: "auto" }}>
          <button
            onClick={handleManualTrade}
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
            手动下单
          </button>
        </div>
      </div>

      {/* ===== 指标卡片 (2列) ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <MobileMetricCard
          label="持仓市值"
          value={`¥${Number(portfolioValue).toLocaleString()}`}
          change={{ text: "+3.2%", type: "up" }}
        />
        <MobileMetricCard
          label="浮动盈亏"
          value={`+¥${Number(portfolioPnl).toLocaleString()}`}
          change={{ text: `+${portfolioPnlPct}%`, type: "up" }}
          valueColor={colors.semantic.up}
        />
        <MobileMetricCard
          label="可用资金"
          value={`¥${Number(availableCash).toLocaleString()}`}
          change={{ text: `占比${positionPct}%`, type: "neutral" }}
        />
        <MobileMetricCard
          label="交易模式"
          value="模拟盘"
          change={{ text: "可升级至半自动", type: "neutral" }}
        />
      </div>

      {/* ===== 当前持仓 ===== */}
      <div style={{ marginBottom: 16 }}>
        <MobileSectionCard title="当前持仓">
          {/* 表头 */}
          <div
            style={{
              display: "flex",
              padding: "8px 14px",
              borderBottom: `1px solid ${colors.border.light}`,
              fontSize: 11,
              color: colors.text.tertiary,
              fontWeight: 500,
              gap: 4,
            }}
          >
            <span style={{ width: 60, flexShrink: 0 }}>代码</span>
            <span style={{ width: 55, flexShrink: 0 }}>名称</span>
            <span style={{ width: 45, flexShrink: 0, textAlign: "right" }}>
              数量
            </span>
            <span style={{ width: 60, flexShrink: 0, textAlign: "right" }}>
              成本
            </span>
            <span style={{ width: 60, flexShrink: 0, textAlign: "right" }}>
              现价
            </span>
            <span style={{ width: 55, flexShrink: 0, textAlign: "right" }}>
              盈亏
            </span>
            <span style={{ width: 50, flexShrink: 0, textAlign: "center" }}>
              操作
            </span>
          </div>

          {positions.map((pos, idx) => {
            const pnlPct = parseFloat(pos.unrealized_pnl_pct);
            const isProfit = pnlPct >= 0;
            return (
              <div
                key={pos.stock_code || idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "10px 14px",
                  gap: 4,
                  fontSize: 12,
                  color: colors.text.primary,
                  borderBottom:
                    idx < positions.length - 1
                      ? `1px solid ${colors.border.light}`
                      : "none",
                }}
              >
                <span
                  style={{
                    width: 60,
                    flexShrink: 0,
                    fontWeight: 500,
                    fontSize: 13,
                  }}
                >
                  {pos.stock_code}
                </span>
                <span
                  style={{
                    width: 55,
                    flexShrink: 0,
                    color: colors.text.secondary,
                  }}
                >
                  {pos.stock_name || ""}
                </span>
                <span
                  style={{
                    width: 45,
                    flexShrink: 0,
                    textAlign: "right",
                    color: colors.text.secondary,
                  }}
                >
                  {pos.total_volume}
                </span>
                <span
                  style={{
                    width: 60,
                    flexShrink: 0,
                    textAlign: "right",
                    color: colors.text.secondary,
                  }}
                >
                  {pos.cost_price}
                </span>
                <span
                  style={{
                    width: 60,
                    flexShrink: 0,
                    textAlign: "right",
                    fontWeight: 500,
                  }}
                >
                  {pos.current_price}
                </span>
                <span
                  style={{
                    width: 55,
                    flexShrink: 0,
                    textAlign: "right",
                    fontWeight: 600,
                    color: isProfit ? colors.semantic.up : colors.semantic.down,
                  }}
                >
                  {isProfit ? "+" : ""}
                  {pnlPct.toFixed(1)}%
                </span>
                <span
                  style={{
                    width: 50,
                    flexShrink: 0,
                    textAlign: "center",
                  }}
                >
                  <button
                    onClick={() => handleStopLoss(pos.stock_code)}
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
                      color: colors.semantic.up,
                      transition: "all 0.15s ease",
                    }}
                  >
                    止损
                  </button>
                </span>
              </div>
            );
          })}
        </MobileSectionCard>
      </div>

      {/* ===== 今日订单 ===== */}
      <MobileSectionCard title="今日订单">
        {/* 表头 */}
        <div
          style={{
            display: "flex",
            padding: "8px 14px",
            borderBottom: `1px solid ${colors.border.light}`,
            fontSize: 11,
            color: colors.text.tertiary,
            fontWeight: 500,
            gap: 4,
          }}
        >
          <span style={{ width: 40, flexShrink: 0 }}>时间</span>
          <span style={{ width: 60, flexShrink: 0 }}>代码</span>
          <span style={{ width: 45, flexShrink: 0, textAlign: "center" }}>
            方向
          </span>
          <span style={{ width: 45, flexShrink: 0, textAlign: "center" }}>
            类型
          </span>
          <span style={{ width: 55, flexShrink: 0, textAlign: "right" }}>
            价格
          </span>
          <span style={{ width: 45, flexShrink: 0, textAlign: "right" }}>
            数量
          </span>
          <span style={{ width: 50, flexShrink: 0, textAlign: "center" }}>
            状态
          </span>
        </div>

        {orders.map((ord, idx) => {
          const isBuy = ord.direction === "buy";
          return (
            <div
              key={ord.id || idx}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "10px 14px",
                gap: 4,
                fontSize: 12,
                color: colors.text.primary,
                borderBottom:
                  idx < orders.length - 1
                    ? `1px solid ${colors.border.light}`
                    : "none",
              }}
            >
              <span
                style={{
                  width: 40,
                  flexShrink: 0,
                  color: colors.text.secondary,
                }}
              >
                {ord.created_at?.slice(11, 16) || ord.created_at || "--"}
              </span>
              <span
                style={{
                  width: 60,
                  flexShrink: 0,
                  fontWeight: 500,
                  fontSize: 13,
                }}
              >
                {ord.stock_code}
              </span>
              <span
                style={{
                  width: 45,
                  flexShrink: 0,
                  textAlign: "center",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    fontSize: 10,
                    fontWeight: 500,
                    lineHeight: 1.3,
                    padding: "1px 7px",
                    borderRadius: 20,
                    backgroundColor: isBuy
                      ? colors.semantic.upBg
                      : colors.semantic.downBg,
                    color: isBuy
                      ? colors.semantic.up
                      : colors.semantic.down,
                  }}
                >
                  {isBuy ? "买入" : "卖出"}
                </span>
              </span>
              <span
                style={{
                  width: 45,
                  flexShrink: 0,
                  textAlign: "center",
                  color: colors.text.secondary,
                }}
              >
                {ord.order_type || (ord.direction === "buy" ? "限价" : "市价")}
              </span>
              <span
                style={{
                  width: 55,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {ord.price || "-"}
              </span>
              <span
                style={{
                  width: 45,
                  flexShrink: 0,
                  textAlign: "right",
                  color: colors.text.secondary,
                }}
              >
                {ord.volume}
              </span>
              <span
                style={{
                  width: 50,
                  flexShrink: 0,
                  textAlign: "center",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    fontSize: 10,
                    fontWeight: 500,
                    lineHeight: 1.3,
                    padding: "1px 7px",
                    borderRadius: 20,
                    backgroundColor:
                      ord.status === "filled"
                        ? colors.semantic.downBg
                        : ord.status === "pending"
                        ? colors.semantic.amberBg
                        : colors.bg.subtle,
                    color:
                      ord.status === "filled"
                        ? colors.semantic.down
                        : ord.status === "pending"
                        ? colors.semantic.amber
                        : colors.text.tertiary,
                  }}
                >
                  {ord.status === "filled"
                    ? "已成交"
                    : ord.status === "pending"
                    ? "待成交"
                    : ord.status === "canceled"
                    ? "已撤销"
                    : ord.status}
                </span>
              </span>
            </div>
          );
        })}
      </MobileSectionCard>
    </div>
  );
}

export default MobileTrade;
