import { useState, useMemo, useEffect, useCallback } from "react";
import {
  Row,
  Col,
  Table,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Tag,
  Space,
  Modal,
  Typography,
  Card,
} from "antd";
import { App } from "antd";
import { colors } from "../../theme/colors";
import type { components } from "../../types/api-generated";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";

type BackendPosition = components["schemas"]["PositionItem"];
type BackendOrder = components["schemas"]["OrderResponse"];

const { Text, Title } = Typography;

/* ============================================================
   Types — UI-layer fields that backend doesn't have
   ============================================================ */
interface OrderDisplay extends BackendOrder {
  stockName: string;
}

/* ============================================================
   Component
   ============================================================ */
const TradePage: React.FC = () => {
  const { message } = App.useApp();

  // ---- state ----
  const [mode, setMode] = useState<string>("SIMULATION");
  const [positions, setPositions] = useState<BackendPosition[]>([]);
  const [orders, setOrders] = useState<OrderDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [modeModalOpen, setModeModalOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState<string | null>(null);
  const [emergencyModalOpen, setEmergencyModalOpen] = useState(false);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [orderForm] = Form.useForm();

  // ---- data fetching ----
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [posData, ordData, modeData] = await Promise.all([
        portfolioService.getPositions(),
        tradeService.getOrders(),
        tradeService.getMode(),
      ]);
      setPositions(posData);
      setOrders(
        ordData.map((o) => ({ ...o, stockName: o.stock_code }))
      );
      if (modeData) setMode(modeData.current_mode);
    } catch (e) {
      console.error("TradePage: failed to load data", e);
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ---- trade-mode tag click handler ----
  const handleModeClick = (target: string) => {
    if (target === mode) return;
    setPendingMode(target);
    setModeModalOpen(true);
  };

  const confirmModeChange = async () => {
    if (!pendingMode) return;
    try {
      await tradeService.updateMode({ target_mode: pendingMode });
      setMode(pendingMode);
      message.success(`交易模式已切换至 ${pendingMode}`);
    } catch {
      message.error("切换模式失败");
    }
    setModeModalOpen(false);
    setPendingMode(null);
  };

  // ---- emergency stop ----
  const handleEmergencyStop = () => setEmergencyModalOpen(true);
  const confirmEmergencyStop = async () => {
    try {
      await tradeService.emergencyStop();
      message.warning("🚨 紧急停止已触发 — 所有交易已暂停");
      setMode("SIMULATION");
    } catch {
      message.error("紧急停止失败");
    }
    setEmergencyModalOpen(false);
  };

  // ---- submit order ----
  const handleSubmitOrder = () => {
    orderForm.validateFields().then(() => setOrderModalOpen(true));
  };

  const confirmSubmitOrder = async () => {
    setIsSubmitting(true);
    try {
      const vals = orderForm.getFieldsValue();
      await tradeService.createOrder({
        stock_code: vals.stockCode,
        direction: vals.direction,
        order_type: vals.orderType,
        price: vals.price ?? 0,
        volume: vals.volume,
        strategy_type: "",
        reason: "",
      });
      message.success("订单已提交");
      setOrderModalOpen(false);
      orderForm.resetFields();
      fetchAll(); // refresh
    } catch {
      message.error("下单失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---- columns ----
  const positionColumns = useMemo(
    () => [
      {
        title: "标的",
        dataIndex: "stock_name",
        key: "stock_name",
        render: (_: string, r: BackendPosition) => (
          <span>
            <span style={{ color: colors.text }}>{r.stock_name}</span>
            <Text style={{ color: colors.dimmed, fontSize: 12, marginLeft: 6 }}>
              {r.stock_code}
            </Text>
          </span>
        ),
      },
      {
        title: "数量",
        dataIndex: "total_volume",
        key: "total_volume",
        width: 100,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.text }}>{v.toLocaleString()}</span>
        ),
      },
      {
        title: "成本",
        dataIndex: "cost_price",
        key: "cost_price",
        width: 100,
        align: "right" as const,
        render: (v: string) => (
          <span style={{ color: colors.muted }}>¥{parseFloat(v || "0").toFixed(2)}</span>
        ),
      },
      {
        title: "市值",
        dataIndex: "market_value",
        key: "market_value",
        width: 100,
        align: "right" as const,
        render: (v: string) => (
          <span style={{ color: colors.text }}>¥{parseFloat(v || "0").toFixed(2)}</span>
        ),
      },
      {
        title: "盈亏%",
        dataIndex: "unrealized_pnl_pct",
        key: "unrealized_pnl_pct",
        width: 100,
        align: "right" as const,
        render: (v: string) => {
          const num = parseFloat(v || "0");
          const sign = num >= 0 ? "+" : "";
          return (
            <span
              style={{
                color: num >= 0 ? colors.danger : colors.success,
                fontWeight: 600,
              }}
            >
              {sign}
              {(num * 100).toFixed(2)}%
            </span>
          );
        },
      },
    ],
    []
  );

  const logColumns = useMemo(
    () => [
      {
        title: "时间",
        dataIndex: "created_at",
        key: "created_at",
        width: 170,
        render: (v: string) => (
          <span style={{ color: colors.muted, fontSize: 13 }}>
            {v ? new Date(v).toLocaleString("zh-CN") : "-"}
          </span>
        ),
      },
      {
        title: "标的",
        key: "stock",
        width: 140,
        render: (_: unknown, r: OrderDisplay) => (
          <span>
            <span style={{ color: colors.text }}>{r.stock_code}</span>
          </span>
        ),
      },
      {
        title: "方向",
        dataIndex: "direction",
        key: "direction",
        width: 80,
        render: (v: string) => (
          <Tag
            color={v === "buy" ? "green" : "red"}
            style={{ borderRadius: 4, fontWeight: 500 }}
          >
            {v === "buy" ? "买入" : "卖出"}
          </Tag>
        ),
      },
      {
        title: "数量",
        dataIndex: "volume",
        key: "volume",
        width: 90,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.text }}>{v.toLocaleString()}</span>
        ),
      },
      {
        title: "成交",
        dataIndex: "filled_volume",
        key: "filled_volume",
        width: 90,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.muted }}>{v.toLocaleString()}</span>
        ),
      },
      {
        title: "价格",
        dataIndex: "price",
        key: "price",
        width: 100,
        align: "right" as const,
        render: (v: string) => (
          <span style={{ color: colors.text }}>¥{parseFloat(v || "0").toFixed(2)}</span>
        ),
      },
      {
        title: "状态",
        dataIndex: "status",
        key: "status",
        width: 90,
        render: (v: string) => {
          const colorMap: Record<string, string> = {
            filled: "success",
            pending: "processing",
            cancelled: "error",
          };
          const labelMap: Record<string, string> = {
            filled: "已成交",
            pending: "待成交",
            cancelled: "已撤销",
          };
          return (
            <Tag color={colorMap[v] || "default"} style={{ borderRadius: 4 }}>
              {labelMap[v] || v}
            </Tag>
          );
        },
      },
    ],
    []
  );

  // ---- watch order type ----
  const orderTypeValue = Form.useWatch("orderType", orderForm);

  return (
    <div style={{ padding: "0 0 24px 0" }}>
      {/* Top bar: mode tags + emergency button */}
      <Title level={3} style={{ color: colors.text, marginBottom: 20 }}>
        交易星图
      </Title>

      <Card
        style={{
          marginBottom: 20,
          background: `${colors.surface} !important`,
          border: `1px solid ${colors.border}`,
          borderRadius: 12,
        }}
        styles={{ body: { padding: "14px 24px" } }}
      >
        <Row align="middle" justify="space-between">
          <Space size={12}>
            {(["SIMULATION", "PAPER", "LIVE"] as const).map((m) => {
              const isActive = mode === m;
              const isLive = m === "LIVE";
              const activeColor = isLive ? colors.danger : colors.shard;
              return (
                <span
                  key={m}
                  onClick={() => handleModeClick(m)}
                  style={{
                    cursor: "pointer",
                    userSelect: "none",
                    padding: "6px 18px",
                    borderRadius: 20,
                    fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    letterSpacing: "0.5px",
                    background: isActive ? `${activeColor}22` : "transparent",
                    border: isActive
                      ? `1.5px solid ${activeColor}`
                      : `1px solid ${colors.dimmed}`,
                    color: isActive ? activeColor : colors.muted,
                    transition: "all 0.25s ease",
                  }}
                >
                  {m === "SIMULATION" ? "💻 模拟" : m === "PAPER" ? "📄 纸交" : "🔥 实盘"}
                </span>
              );
            })}
          </Space>

          {mode === "LIVE" && (
            <Button
              danger
              size="large"
              icon={<span>🚨</span>}
              onClick={handleEmergencyStop}
              style={{
                animation: "pulse-emergency 1.5s ease-in-out infinite",
                fontWeight: 700,
                fontSize: 14,
                borderRadius: 8,
                border: "none",
                background: `${colors.danger} !important`,
                color: "#fff",
                boxShadow: `0 0 20px ${colors.danger}66`,
              }}
            >
              紧急停止
            </Button>
          )}
        </Row>
      </Card>

      {/* Positions + Order form */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                📊 当前持仓
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
            styles={{ body: { padding: 0 } }}
          >
            <Table
              dataSource={positions}
              columns={positionColumns}
              rowKey="stock_code"
              size="small"
              loading={loading}
              pagination={false}
              locale={{
                emptyText: <span style={{ color: colors.muted }}>暂无持仓</span>,
              }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                🚀 新订单
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
          >
            <Form
              form={orderForm}
              layout="vertical"
              requiredMark={false}
              initialValues={{
                direction: "buy",
                orderType: "market",
                volume: 100,
              }}
              style={{ maxWidth: "100%" }}
            >
              <Form.Item
                name="stockCode"
                label={<span style={{ color: colors.muted }}>股票代码 *</span>}
                rules={[{ required: true, message: "请输入股票代码" }]}
              >
                <Input
                  placeholder="例如 600519"
                  style={{
                    background: colors.bg,
                    borderColor: colors.border,
                    color: colors.text,
                    borderRadius: 6,
                  }}
                />
              </Form.Item>

              <Form.Item
                name="direction"
                label={<span style={{ color: colors.muted }}>方向</span>}
              >
                <Select
                  style={{ background: colors.bg, borderRadius: 6 }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="buy">买入</Select.Option>
                  <Select.Option value="sell">卖出</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="orderType"
                label={<span style={{ color: colors.muted }}>订单类型</span>}
              >
                <Select
                  style={{ background: colors.bg, borderRadius: 6 }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="market">市价</Select.Option>
                  <Select.Option value="limit">限价</Select.Option>
                </Select>
              </Form.Item>

              {orderTypeValue === "limit" && (
                <Form.Item
                  name="price"
                  label={<span style={{ color: colors.muted }}>限价价格</span>}
                  rules={[{ required: true, message: "请输入限价价格" }]}
                >
                  <InputNumber
                    min={0.01}
                    step={0.01}
                    precision={2}
                    prefix="¥"
                    style={{
                      width: "100%",
                      background: colors.bg,
                      borderColor: colors.border,
                      borderRadius: 6,
                    }}
                  />
                </Form.Item>
              )}

              <Form.Item
                name="volume"
                label={<span style={{ color: colors.muted }}>数量 *</span>}
                rules={[
                  { required: true, message: "请输入数量" },
                  { type: "number", min: 100, message: "最小数量为100" },
                ]}
              >
                <InputNumber
                  min={100}
                  step={100}
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderColor: colors.border,
                    borderRadius: 6,
                  }}
                />
              </Form.Item>

              <Form.Item
                name="stopLossPrice"
                label={<span style={{ color: colors.muted }}>止损价（可选）</span>}
              >
                <InputNumber
                  min={0.01}
                  step={0.01}
                  precision={2}
                  prefix="¥"
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderColor: colors.border,
                    borderRadius: 6,
                  }}
                />
              </Form.Item>

              <Form.Item
                name="stopProfitPrice"
                label={<span style={{ color: colors.muted }}>止盈价（可选）</span>}
              >
                <InputNumber
                  min={0.01}
                  step={0.01}
                  precision={2}
                  prefix="¥"
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderColor: colors.border,
                    borderRadius: 6,
                  }}
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 0 }}>
                <Button
                  type="primary"
                  block
                  size="large"
                  loading={isSubmitting}
                  disabled={mode === "SIMULATION"}
                  onClick={handleSubmitOrder}
                  style={{
                    borderRadius: 8,
                    height: 44,
                    fontSize: 15,
                    fontWeight: 600,
                    opacity: mode === "SIMULATION" ? 0.5 : 1,
                  }}
                >
                  {mode === "SIMULATION"
                    ? "模拟模式 — 无法下单"
                    : mode === "LIVE"
                    ? "🔥 实盘下单"
                    : "📄 纸交下单"}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>

      {/* Trade log */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                📜 交易日志
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
          >
            <Table
              dataSource={orders}
              columns={logColumns}
              rowKey="id"
              size="small"
              loading={loading}
              pagination={{ pageSize: 10, size: "small" }}
              locale={{
                emptyText: <span style={{ color: colors.muted }}>暂无交易日志</span>,
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Modals */}
      <Modal
        title={<span style={{ color: colors.text }}>切换交易模式</span>}
        open={modeModalOpen}
        onOk={confirmModeChange}
        onCancel={() => {
          setModeModalOpen(false);
          setPendingMode(null);
        }}
        okText="确认切换"
        cancelText="取消"
        centered
        styles={{
          header: { background: colors.card, borderRadius: 8 },
          content: {
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
          },
          footer: { borderTop: `1px solid ${colors.border}` },
        }}
      >
        <Text style={{ color: colors.muted }}>
          确认从{" "}
          <Text strong style={{ color: colors.text }}>
            {mode}
          </Text>{" "}
          切换到{" "}
          <Text strong style={{ color: pendingMode === "LIVE" ? colors.danger : colors.shard }}>
            {pendingMode}
          </Text>
          ？
        </Text>
      </Modal>

      <Modal
        title={
          <span style={{ color: colors.danger, fontWeight: 700 }}>
            🚨 紧急停止确认
          </span>
        }
        open={emergencyModalOpen}
        onOk={confirmEmergencyStop}
        onCancel={() => setEmergencyModalOpen(false)}
        okText="确认紧急停止"
        cancelText="取消"
        okButtonProps={{ danger: true, style: { fontWeight: 600, borderRadius: 6 } }}
        centered
        styles={{
          header: { background: colors.card, borderRadius: 8 },
          content: {
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
          },
          footer: { borderTop: `1px solid ${colors.border}` },
        }}
      >
        <Text style={{ color: colors.muted }}>
          此操作将立即{" "}
          <Text strong style={{ color: colors.danger }}>
            暂停所有交易活动
          </Text>
          ，包括所有挂单、止损策略和自动化交易。确认执行？
        </Text>
      </Modal>

      <Modal
        title={
          <span style={{ color: colors.text, fontWeight: 600 }}>
            📋 确认订单
          </span>
        }
        open={orderModalOpen}
        onOk={confirmSubmitOrder}
        onCancel={() => setOrderModalOpen(false)}
        confirmLoading={isSubmitting}
        okText="确认下单"
        cancelText="取消"
        centered
        styles={{
          header: { background: colors.card, borderRadius: 8 },
          content: {
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
          },
          footer: { borderTop: `1px solid ${colors.border}` },
        }}
      >
        {(() => {
          const vals = orderForm.getFieldsValue();
          return (
            <div>
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}><Text style={{ color: colors.muted }}>股票</Text></Col>
                <Col span={14}><Text style={{ color: colors.text }}>{vals.stockCode}</Text></Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}><Text style={{ color: colors.muted }}>方向</Text></Col>
                <Col span={14}>
                  <Tag color={vals.direction === "buy" ? "green" : "red"} style={{ borderRadius: 4 }}>
                    {vals.direction === "buy" ? "买入" : "卖出"}
                  </Tag>
                </Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}><Text style={{ color: colors.muted }}>类型</Text></Col>
                <Col span={14}>
                  <Text style={{ color: colors.text }}>
                    {vals.orderType === "market" ? "市价" : "限价"}
                  </Text>
                </Col>
              </Row>
              {vals.price != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}><Text style={{ color: colors.muted }}>价格</Text></Col>
                  <Col span={14}>
                    <Text style={{ color: colors.text }}>¥{vals.price?.toFixed(2)}</Text>
                  </Col>
                </Row>
              )}
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}><Text style={{ color: colors.muted }}>数量</Text></Col>
                <Col span={14}>
                  <Text style={{ color: colors.text }}>{vals.volume?.toLocaleString()} 股</Text>
                </Col>
              </Row>
              {vals.stopLossPrice != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}><Text style={{ color: colors.muted }}>止损价</Text></Col>
                  <Col span={14}>
                    <Text style={{ color: colors.danger }}>¥{vals.stopLossPrice?.toFixed(2)}</Text>
                  </Col>
                </Row>
              )}
              {vals.stopProfitPrice != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}><Text style={{ color: colors.muted }}>止盈价</Text></Col>
                  <Col span={14}>
                    <Text style={{ color: colors.success }}>¥{vals.stopProfitPrice?.toFixed(2)}</Text>
                  </Col>
                </Row>
              )}
            </div>
          );
        })()}
      </Modal>

      <style>{`
        @keyframes pulse-emergency {
          0%, 100% { transform: scale(1); box-shadow: 0 0 12px ${colors.danger}44; }
          50% { transform: scale(1.03); box-shadow: 0 0 28px ${colors.danger}99; }
        }
      `}</style>
    </div>
  );
};

export default TradePage;
