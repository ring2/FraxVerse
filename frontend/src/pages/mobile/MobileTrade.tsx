import { useCallback, useEffect, useRef, useState } from "react";
import { App, Modal, Form, Input, InputNumber, Radio } from "antd";
import { useTheme } from "../../theme/ThemeContext";
import {
  MobileMetricCard,
  MobileSectionCard,
} from "../../components/mobile";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";

function MobileTrade() {
  const { message, modal } = App.useApp();
  const { colors } = useTheme();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [positions, setPositions] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [orders, setOrders] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [portfolio, setPortfolio] = useState<Record<string, any> | null>(null);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);
  const [orderType, setOrderType] = useState<"market" | "limit">("market");
  const [submitting, setSubmitting] = useState(false);
  const cancelledRef = useRef(false);

  const fetchData = useCallback(async () => {
    cancelledRef.current = false;
    try {
      const [p, o, s] = await Promise.all([
        portfolioService.getPositions().catch(() => null),
        tradeService.getOrders().catch(() => null),
        portfolioService.getSummary().catch(() => null),
      ]);
      if (cancelledRef.current) return;
      setPositions(p || []);
      setOrders(o || []);
      setPortfolio(s);
    } catch {
      if (!cancelledRef.current) {
        setPositions([]);
        setOrders([]);
        setPortfolio(null);
      }
    } finally {
      if (!cancelledRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    return () => {
      cancelledRef.current = true;
    };
  }, [fetchData]);

  const handleStopLoss = useCallback(
    (code: string) => {
      modal.confirm({
        title: "确认止损",
        content: `确定对 ${code} 执行止损？`,
        okText: "确认止损",
        cancelText: "取消",
        onOk: async () => {
          try {
            await tradeService.emergencyStop();
            message.success("已触发紧急停止");
            fetchData();
          } catch (err: unknown) {
            const msg =
              err instanceof Error ? err.message : "未知错误";
            message.error(`止损失败: ${msg}`);
          }
        },
      });
    },
    [modal, message, fetchData]
  );

  const handleManualTrade = useCallback(() => {
    setOrderType("market");
    form.resetFields();
    setTradeModalOpen(true);
  }, [form]);

  const handleSubmitOrder = useCallback(async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload: {
        stock_code: string;
        direction: string;
        order_type: string;
        volume: number;
        price?: number | string;
      } = {
        stock_code: values.stock_code.toUpperCase(),
        direction: values.direction,
        order_type: orderType,
        volume: values.volume,
      };

      if (orderType === "limit") {
        payload.price = values.price;
      }

      await tradeService.createOrder(payload);
      message.success("订单已提交");
      setTradeModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "errorFields" in err) {
        // Form validation error — ignore
        return;
      }
      const msg =
        err instanceof Error ? err.message : "未知错误";
      message.error(`下单失败: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  }, [form, orderType, message, fetchData]);

  const handleExportReport = useCallback(() => {
    message.info("导出报表 — 开发中");
  }, [message]);

  const portfolioValue = portfolio?.total_market_value ?? 0;
  const portfolioPnl = portfolio?.total_pnl ?? 0;
  const portfolioPnlPct = portfolio?.total_pnl_pct ?? 0;
  const availableCash = portfolio?.available_cash ?? 0;
  const positionPct = portfolio?.total_position_pct ?? 0;

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
          交易
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button
            onClick={handleExportReport}
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
              border: `1px solid ${colors.border.medium}`,
              outline: "none",
              background: "transparent",
              color: colors.text.secondary,
              transition: "all 0.15s ease",
            }}
          >
            导出报表
          </button>
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
              transition: "all 0.15s ease",
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
      {/* ===== 手动下单弹窗 ===== */}
      <Modal
        title="手动下单"
        open={tradeModalOpen}
        onCancel={() => setTradeModalOpen(false)}
        footer={null}
        width={340}
        destroyOnClose
        styles={{
          mask: { background: "rgba(0,0,0,0.45)" },
          content: { borderRadius: colors.radius.md },
        }}
      >
        <Form
          form={form}
          layout="vertical"
          size="middle"
          style={{ marginTop: 8 }}
          initialValues={{ direction: "buy" }}
        >
          <Form.Item
            label="股票代码"
            name="stock_code"
            rules={[{ required: true, message: "请输入股票代码" }]}
          >
            <Input
              placeholder="例如 600519"
              maxLength={6}
              style={{ textTransform: "uppercase" }}
              onInput={(e) => {
                const target = e.target as HTMLInputElement;
                target.value = target.value.toUpperCase();
              }}
            />
          </Form.Item>

          <Form.Item label="方向" name="direction">
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              style={{ display: "flex", gap: 8 }}
            >
              <Radio.Button
                value="buy"
                style={{
                  flex: 1,
                  textAlign: "center",
                }}
              >
                买入
              </Radio.Button>
              <Radio.Button
                value="sell"
                style={{
                  flex: 1,
                  textAlign: "center",
                }}
              >
                卖出
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label="数量"
            name="volume"
            rules={[{ required: true, message: "请输入数量" }]}
          >
            <InputNumber
              style={{ width: "100%" }}
              min={1}
              step={100}
              placeholder="请输入数量"
            />
          </Form.Item>

          <Form.Item label="价格类型">
            <Radio.Group
              value={orderType}
              onChange={(e) => setOrderType(e.target.value)}
              optionType="button"
              buttonStyle="solid"
              style={{ display: "flex", gap: 8 }}
            >
              <Radio.Button value="market" style={{ flex: 1, textAlign: "center" }}>
                市价
              </Radio.Button>
              <Radio.Button value="limit" style={{ flex: 1, textAlign: "center" }}>
                限价
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          {orderType === "limit" && (
            <Form.Item
              label="限价价格"
              name="price"
              rules={[
                { required: true, message: "请输入限价价格" },
                {
                  type: "number",
                  min: 0.01,
                  message: "价格必须大于0",
                },
              ]}
            >
              <InputNumber
                style={{ width: "100%" }}
                min={0.01}
                step={0.01}
                precision={2}
                prefix="¥"
                placeholder="请输入限价价格"
              />
            </Form.Item>
          )}

          <Form.Item style={{ marginBottom: 0 }}>
            <button
              onClick={handleSubmitOrder}
              disabled={submitting}
              style={{
                display: "block",
                width: "100%",
                padding: "10px 0",
                borderRadius: `${colors.radius.md}px`,
                fontSize: 15,
                fontWeight: 600,
                lineHeight: 1.4,
                cursor: submitting ? "not-allowed" : "pointer",
                border: "none",
                outline: "none",
                background: submitting
                  ? colors.border.medium
                  : colors.gradient.primary,
                color: colors.text.inverse,
                boxShadow: colors.btnShadow,
                opacity: submitting ? 0.6 : 1,
                transition: "all 0.15s ease",
              }}
            >
              {submitting ? "提交中..." : "提交订单"}
            </button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default MobileTrade;
