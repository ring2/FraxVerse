import { useState, useMemo } from "react";
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
  DatePicker,
  Card,
  message,
} from "antd";
import { colors } from "../../theme/colors";
import type {
  PositionItem,
  TradeOrder,
  StopLossCondition,
  TradeMode,
  SubmitOrderRequest,
} from "../../types/trade";

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;

/* ============================================================
   Mock Data
   ============================================================ */
const mockPositions: PositionItem[] = [
  {
    id: "p1",
    stockCode: "600519",
    stockName: "贵州茅台",
    volume: 100,
    avgCost: 1850.0,
    currentPrice: 1893.5,
    marketValue: 189350,
    pnl: 4350,
    pnlPct: 2.35,
    strategy: "价值投资",
    openedAt: "2025-01-15",
  },
  {
    id: "p2",
    stockCode: "300750",
    stockName: "宁德时代",
    volume: 500,
    avgCost: 245.0,
    currentPrice: 241.86,
    marketValue: 120930,
    pnl: -1570,
    pnlPct: -1.28,
    strategy: "动量策略",
    openedAt: "2025-03-20",
  },
  {
    id: "p3",
    stockCode: "000001",
    stockName: "平安银行",
    volume: 1000,
    avgCost: 11.5,
    currentPrice: 11.6,
    marketValue: 11600,
    pnl: 100,
    pnlPct: 0.87,
    strategy: "网格策略",
    openedAt: "2025-04-01",
  },
];

const mockStopLosses: StopLossCondition[] = [
  {
    id: "sl1",
    stockCode: "600519",
    stockName: "贵州茅台",
    type: "fixed",
    triggerPrice: 1820.0,
    currentPrice: 1893.5,
    status: "active",
    createdAt: "2025-04-10 09:30",
  },
  {
    id: "sl2",
    stockCode: "300750",
    stockName: "宁德时代",
    type: "trailing",
    triggerPrice: 235.0,
    currentPrice: 241.86,
    status: "active",
    createdAt: "2025-04-12 14:15",
  },
];

const mockTradeLogs: (TradeOrder & { stockName: string })[] = [
  {
    id: "t1",
    stockCode: "600519",
    stockName: "贵州茅台",
    direction: "buy",
    orderType: "limit",
    price: 1840.0,
    volume: 100,
    filledVolume: 100,
    status: "filled",
    createdAt: "2025-04-08 09:35:12",
    updatedAt: "2025-04-08 09:35:15",
  },
  {
    id: "t2",
    stockCode: "300750",
    stockName: "宁德时代",
    direction: "sell",
    orderType: "market",
    price: 242.5,
    volume: 200,
    filledVolume: 200,
    status: "filled",
    createdAt: "2025-04-09 10:20:45",
    updatedAt: "2025-04-09 10:20:46",
  },
  {
    id: "t3",
    stockCode: "000001",
    stockName: "平安银行",
    direction: "buy",
    orderType: "limit",
    price: 11.45,
    volume: 1000,
    filledVolume: 1000,
    status: "filled",
    createdAt: "2025-04-10 11:05:33",
    updatedAt: "2025-04-10 11:05:35",
  },
  {
    id: "t4",
    stockCode: "600519",
    stockName: "贵州茅台",
    direction: "buy",
    orderType: "limit",
    price: 1855.0,
    volume: 100,
    filledVolume: 0,
    status: "pending",
    createdAt: "2025-04-11 13:45:00",
    updatedAt: "2025-04-11 13:45:00",
  },
  {
    id: "t5",
    stockCode: "300750",
    stockName: "宁德时代",
    direction: "sell",
    orderType: "limit",
    price: 250.0,
    volume: 300,
    filledVolume: 0,
    status: "cancelled",
    createdAt: "2025-04-12 09:15:22",
    updatedAt: "2025-04-12 10:30:00",
  },
];

/* ============================================================
   Component
   ============================================================ */
const TradePage: React.FC = () => {
  // ---- state ----
  const [mode, setMode] = useState<TradeMode>("SIMULATION");
  const [modeModalOpen, setModeModalOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState<TradeMode | null>(null);
  const [emergencyModalOpen, setEmergencyModalOpen] = useState(false);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [orderForm] = Form.useForm<SubmitOrderRequest>();

  // ---- trade-mode tag click handler ----
  const handleModeClick = (target: TradeMode) => {
    if (target === mode) return;
    setPendingMode(target);
    setModeModalOpen(true);
  };

  const confirmModeChange = () => {
    if (pendingMode) setMode(pendingMode);
    setModeModalOpen(false);
    setPendingMode(null);
  };

  // ---- emergency stop ----
  const handleEmergencyStop = () => setEmergencyModalOpen(true);
  const confirmEmergencyStop = () => {
    message.warning("🚨 紧急停止已触发 — 所有交易已暂停");
    setMode("SIMULATION");
    setEmergencyModalOpen(false);
  };

  const handleSubmitOrder = () => {
    orderForm.validateFields().then(() => setOrderModalOpen(true));
  };

  const confirmSubmitOrder = async () => {
    setIsSubmitting(true);
    // simulate network delay
    await new Promise((r) => setTimeout(r, 800));
    message.success("订单已提交");
    setIsSubmitting(false);
    setOrderModalOpen(false);
    orderForm.resetFields();
  };

  // ---- helper: pnl color ----
  // (unused, kept for reference)
  // const getPnlColor = (v: number) => (v >= 0 ? colors.danger : colors.success);

  // ---- columns ----
  const positionColumns = useMemo(
    () => [
      {
        title: "标的",
        dataIndex: "stockName",
        key: "stockName",
        render: (_: string, r: PositionItem) => (
          <span>
            <span style={{ color: colors.text }}>{r.stockName}</span>
            <Text
              style={{
                color: colors.dimmed,
                fontSize: 12,
                marginLeft: 6,
              }}
            >
              {r.stockCode}
            </Text>
          </span>
        ),
      },
      {
        title: "数量",
        dataIndex: "volume",
        key: "volume",
        width: 100,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.text }}>{v.toLocaleString()}</span>
        ),
      },
      {
        title: "成本",
        dataIndex: "avgCost",
        key: "avgCost",
        width: 100,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.muted }}>¥{v.toFixed(2)}</span>
        ),
      },
      {
        title: "现价",
        dataIndex: "currentPrice",
        key: "currentPrice",
        width: 100,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.text }}>¥{v.toFixed(2)}</span>
        ),
      },
      {
        title: "盈亏%",
        dataIndex: "pnlPct",
        key: "pnlPct",
        width: 100,
        align: "right" as const,
        render: (v: number) => {
          const sign = v >= 0 ? "+" : "";
          return (
            <span
              style={{
                color: v >= 0 ? colors.danger : colors.success,
                fontWeight: 600,
              }}
            >
              {sign}
              {v.toFixed(2)}%
            </span>
          );
        },
      },
    ],
    []
  );

  const stopLossColumns = useMemo(
    () => [
      {
        title: "标的",
        dataIndex: "stockName",
        key: "stockName",
        render: (_: string, r: StopLossCondition) => (
          <span>
            <span style={{ color: colors.text }}>{r.stockName}</span>
            <Text
              style={{
                color: colors.dimmed,
                fontSize: 12,
                marginLeft: 6,
              }}
            >
              {r.stockCode}
            </Text>
          </span>
        ),
      },
      {
        title: "类型",
        dataIndex: "type",
        key: "type",
        width: 120,
        render: (v: string) => (
          <Tag
            color={v === "fixed" ? "blue" : "orange"}
            style={{ borderRadius: 4 }}
          >
            {v === "fixed" ? "固定止损" : "追踪止损"}
          </Tag>
        ),
      },
      {
        title: "触发价",
        dataIndex: "triggerPrice",
        key: "triggerPrice",
        width: 110,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.amber }}>¥{v.toFixed(2)}</span>
        ),
      },
      {
        title: "现价",
        dataIndex: "currentPrice",
        key: "currentPrice",
        width: 110,
        align: "right" as const,
        render: (v: number) => (
          <span style={{ color: colors.text }}>¥{v.toFixed(2)}</span>
        ),
      },
    ],
    []
  );

  const logColumns = useMemo(
    () => [
      {
        title: "时间",
        dataIndex: "createdAt",
        key: "createdAt",
        width: 170,
        render: (v: string) => (
          <span style={{ color: colors.muted, fontSize: 13 }}>{v}</span>
        ),
      },
      {
        title: "标的",
        key: "stock",
        width: 140,
        render: (_: unknown, r: TradeOrder & { stockName: string }) => (
          <span>
            <span style={{ color: colors.text }}>{r.stockName}</span>
            <Text style={{ color: colors.dimmed, fontSize: 12, marginLeft: 4 }}>
              {r.stockCode}
            </Text>
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
        title: "类型",
        dataIndex: "orderType",
        key: "orderType",
        width: 80,
        render: (v: string) => (
          <span style={{ color: colors.muted }}>
            {v === "market" ? "市价" : "限价"}
          </span>
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

  // ---- watch order type to conditionally show limit price ----
  const orderTypeValue = Form.useWatch("orderType", orderForm);

  return (
    <div style={{ padding: "0 0 24px 0" }}>
      {/* ================================================================
          Top bar: mode tags + emergency button
          ================================================================ */}
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
        bodyStyle={{ padding: "14px 24px" }}
      >
        <Row align="middle" justify="space-between">
          {/* Mode tags */}
          <Space size={12}>
            {(["SIMULATION", "PAPER", "LIVE"] as TradeMode[]).map((m) => {
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
                    background: isActive
                      ? `${activeColor}22`
                      : "transparent",
                    border: isActive
                      ? `1.5px solid ${activeColor}`
                      : `1px solid ${colors.dimmed}`,
                    color: isActive ? activeColor : colors.muted,
                    transition: "all 0.25s ease",
                  }}
                >
                  {m === "SIMULATION"
                    ? "💻 模拟"
                    : m === "PAPER"
                    ? "📄 纸交"
                    : "🔥 实盘"}
                </span>
              );
            })}
          </Space>

          {/* Emergency stop — only in LIVE mode */}
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

      {/* ================================================================
          Middle: Positions (left 14/24) + Order form (right 10/24)
          ================================================================ */}
      <Row gutter={[16, 16]}>
        {/* Left — Positions */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                📊 当前持仓
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
            bodyStyle={{ padding: 0 }}
          >
            <Table
              dataSource={mockPositions}
              columns={positionColumns}
              rowKey="id"
              size="small"
              pagination={false}
              locale={{
                emptyText: (
                  <span style={{ color: colors.muted }}>暂无持仓</span>
                ),
              }}
            />
          </Card>
        </Col>

        {/* Right — Order Form */}
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
              {/* 股票代码 */}
              <Form.Item
                name="stockCode"
                label={<span style={{ color: colors.muted }}>股票代码 *</span>}
                rules={[
                  { required: true, message: "请输入股票代码" },
                ]}
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

              {/* 方向 */}
              <Form.Item
                name="direction"
                label={<span style={{ color: colors.muted }}>方向</span>}
              >
                <Select
                  style={{
                    background: colors.bg,
                    borderRadius: 6,
                  }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="buy">买入</Select.Option>
                  <Select.Option value="sell">卖出</Select.Option>
                </Select>
              </Form.Item>

              {/* 订单类型 */}
              <Form.Item
                name="orderType"
                label={<span style={{ color: colors.muted }}>订单类型</span>}
              >
                <Select
                  style={{
                    background: colors.bg,
                    borderRadius: 6,
                  }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="market">市价</Select.Option>
                  <Select.Option value="limit">限价</Select.Option>
                </Select>
              </Form.Item>

              {/* 限价价格 (conditional) */}
              {orderTypeValue === "limit" && (
                <Form.Item
                  name="price"
                  label={<span style={{ color: colors.muted }}>限价价格</span>}
                  rules={[
                    { required: true, message: "请输入限价价格" },
                  ]}
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

              {/* 数量 */}
              <Form.Item
                name="volume"
                label={<span style={{ color: colors.muted }}>数量 *</span>}
                rules={[
                  { required: true, message: "请输入数量" },
                  {
                    type: "number",
                    min: 100,
                    message: "最小数量为100",
                  },
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

              {/* 止损价 */}
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

              {/* 止盈价 */}
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

              {/* 下单按钮 */}
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

      {/* ================================================================
          Bottom: Stop-loss conditions + Trade log
          ================================================================ */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* Stop-loss conditions */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                🛡 止损条件
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
            bodyStyle={{ padding: 0 }}
          >
            <Table
              dataSource={mockStopLosses}
              columns={stopLossColumns}
              rowKey="id"
              size="small"
              pagination={false}
              locale={{
                emptyText: (
                  <span style={{ color: colors.muted }}>暂无止损条件</span>
                ),
              }}
            />
          </Card>
        </Col>

        {/* Trade log */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <span style={{ color: colors.text, fontSize: 15, fontWeight: 600 }}>
                📜 交易日志
              </span>
            }
            headStyle={{ borderBottom: `1px solid ${colors.border}` }}
          >
            {/* Filters */}
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={8}>
                <RangePicker
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderColor: colors.border,
                    borderRadius: 6,
                  }}
                  popupClassName="range-picker-cosmos"
                />
              </Col>
              <Col xs={12} sm={5}>
                <Input
                  placeholder="搜索代码"
                  style={{
                    background: colors.bg,
                    borderColor: colors.border,
                    color: colors.text,
                    borderRadius: 6,
                  }}
                />
              </Col>
              <Col xs={12} sm={5}>
                <Select
                  placeholder="策略"
                  allowClear
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderRadius: 6,
                  }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="all">全部</Select.Option>
                  <Select.Option value="value">价值投资</Select.Option>
                  <Select.Option value="momentum">动量策略</Select.Option>
                  <Select.Option value="grid">网格策略</Select.Option>
                </Select>
              </Col>
              <Col xs={12} sm={6}>
                <Select
                  placeholder="事件"
                  allowClear
                  style={{
                    width: "100%",
                    background: colors.bg,
                    borderRadius: 6,
                  }}
                  dropdownStyle={{ background: colors.card }}
                >
                  <Select.Option value="all">全部</Select.Option>
                  <Select.Option value="buy">买入</Select.Option>
                  <Select.Option value="sell">卖出</Select.Option>
                  <Select.Option value="sl">止损触发</Select.Option>
                  <Select.Option value="tp">止盈触发</Select.Option>
                </Select>
              </Col>
            </Row>

            <Table
              dataSource={mockTradeLogs}
              columns={logColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 5, size: "small" }}
              locale={{
                emptyText: (
                  <span style={{ color: colors.muted }}>暂无交易日志</span>
                ),
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* ================================================================
          Modals
          ================================================================ */}

      {/* Mode switch confirm */}
      <Modal
        title={
          <span style={{ color: colors.text }}>
            切换交易模式
          </span>
        }
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

      {/* Emergency stop confirm */}
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
        okButtonProps={{
          danger: true,
          style: {
            fontWeight: 600,
            borderRadius: 6,
          },
        }}
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
          此操作将立即{""}
          <Text strong style={{ color: colors.danger }}>
            暂停所有交易活动
          </Text>
          ，包括所有挂单、止损策略和自动化交易。确认执行？
        </Text>
      </Modal>

      {/* Order submit confirm */}
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
                <Col span={10}>
                  <Text style={{ color: colors.muted }}>股票</Text>
                </Col>
                <Col span={14}>
                  <Text style={{ color: colors.text }}>{vals.stockCode}</Text>
                </Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}>
                  <Text style={{ color: colors.muted }}>方向</Text>
                </Col>
                <Col span={14}>
                  <Tag
                    color={vals.direction === "buy" ? "green" : "red"}
                    style={{ borderRadius: 4 }}
                  >
                    {vals.direction === "buy" ? "买入" : "卖出"}
                  </Tag>
                </Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}>
                  <Text style={{ color: colors.muted }}>类型</Text>
                </Col>
                <Col span={14}>
                  <Text style={{ color: colors.text }}>
                    {vals.orderType === "market" ? "市价" : "限价"}
                  </Text>
                </Col>
              </Row>
              {vals.price != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}>
                    <Text style={{ color: colors.muted }}>价格</Text>
                  </Col>
                  <Col span={14}>
                    <Text style={{ color: colors.text }}>
                      ¥{vals.price?.toFixed(2)}
                    </Text>
                  </Col>
                </Row>
              )}
              <Row style={{ marginBottom: 8 }}>
                <Col span={10}>
                  <Text style={{ color: colors.muted }}>数量</Text>
                </Col>
                <Col span={14}>
                  <Text style={{ color: colors.text }}>
                    {vals.volume?.toLocaleString()} 股
                  </Text>
                </Col>
              </Row>
              {vals.stopLossPrice != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}>
                    <Text style={{ color: colors.muted }}>止损价</Text>
                  </Col>
                  <Col span={14}>
                    <Text style={{ color: colors.danger }}>
                      ¥{vals.stopLossPrice?.toFixed(2)}
                    </Text>
                  </Col>
                </Row>
              )}
              {vals.stopProfitPrice != null && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={10}>
                    <Text style={{ color: colors.muted }}>止盈价</Text>
                  </Col>
                  <Col span={14}>
                    <Text style={{ color: colors.success }}>
                      ¥{vals.stopProfitPrice?.toFixed(2)}
                    </Text>
                  </Col>
                </Row>
              )}
            </div>
          );
        })()}
      </Modal>

      {/* Inline keyframes for emergency pulse animation */}
      <style>{`
        @keyframes pulse-emergency {
          0%, 100% {
            transform: scale(1);
            box-shadow: 0 0 12px ${colors.danger}44;
          }
          50% {
            transform: scale(1.03);
            box-shadow: 0 0 28px ${colors.danger}99;
          }
        }
      `}</style>
    </div>
  );
};

export default TradePage;
