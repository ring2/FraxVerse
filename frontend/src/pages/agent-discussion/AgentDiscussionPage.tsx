import { useState } from "react";
import { Card, Select, Tag, Typography, Row, Col, Table } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import type { AgentOpinion, AgentWeight } from "../../types/agent";

const { Title, Text, Paragraph } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

const targetOptions = [
  { value: "贵州茅台", label: "贵州茅台" },
  { value: "宁德时代", label: "宁德时代" },
  { value: "平安银行", label: "平安银行" },
];

const mockOpinions: AgentOpinion[] = [
  {
    agentId: "1",
    agentName: "趋势猎手",
    action: "buy",
    reason: "均线多头排列，量能持续放大，短期动能强劲。",
    confidence: 85,
    refuteReason: undefined,
  },
  {
    agentId: "2",
    agentName: "价值守望者",
    action: "hold",
    reason: "估值处于合理区间，等待更明确的财报信号。",
    confidence: 70,
    refuteReason: "但若Q3营收低于预期则需重新评估",
  },
  {
    agentId: "3",
    agentName: "风险守护者",
    action: "sell",
    reason: "市场波动率上升，仓位过重风险较高。",
    confidence: 75,
    refuteReason: undefined,
  },
  {
    agentId: "4",
    agentName: "情绪感知者",
    action: "buy",
    reason: "市场恐慌指数回落，资金流向积极。",
    confidence: 80,
    refuteReason: "若突然出现黑天鹅事件则止损",
  },
];

const mockWeights: AgentWeight[] = [
  { agentId: "1", agentName: "趋势猎手", weight: 0.3, winRate: 0.62, totalDecisions: 158 },
  { agentId: "2", agentName: "价值守望者", weight: 0.25, winRate: 0.58, totalDecisions: 134 },
  { agentId: "3", agentName: "风险守护者", weight: 0.25, winRate: 0.71, totalDecisions: 112 },
  { agentId: "4", agentName: "情绪感知者", weight: 0.2, winRate: 0.55, totalDecisions: 96 },
];

const consensusAction = "buy" as const;
const consensusScore = 78;
const currentRound = 3;
const stockName = "贵州茅台";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const actionConfig: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  buy: {
    color: colors.danger,
    icon: <CheckCircleOutlined />,
    label: "买入",
  },
  sell: {
    color: colors.success,
    icon: <CloseCircleOutlined />,
    label: "卖出",
  },
  hold: {
    color: colors.amber,
    icon: <MinusCircleOutlined />,
    label: "持有",
  },
};

function actionTag(action: string) {
  const cfg = actionConfig[action];
  return (
    <Tag color={cfg.color} icon={cfg.icon}>
      {cfg.label}
    </Tag>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────

const AgentDiscussionPage: React.FC = () => {
  const [target, setTarget] = useState<string>("贵州茅台");

  const weightColumns = [
    {
      title: "Agent",
      dataIndex: "agentName",
      key: "agentName",
      render: (v: string) => (
        <span style={{ color: colors.text }}>{v}</span>
      ),
    },
    {
      title: "权重",
      dataIndex: "weight",
      key: "weight",
      render: (v: number) => (
        <span style={{ color: colors.gold }}>{(v * 100).toFixed(0)}%</span>
      ),
    },
    {
      title: "胜率",
      dataIndex: "winRate",
      key: "winRate",
      render: (v: number) => (
        <span style={{ color: colors.shard }}>{(v * 100).toFixed(1)}%</span>
      ),
    },
    {
      title: "总决策数",
      dataIndex: "totalDecisions",
      key: "totalDecisions",
      render: (v: number) => (
        <span style={{ color: colors.muted }}>{v}</span>
      ),
    },
  ];

  return (
    <div>
      {/* ── 标题行 ── */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ color: colors.text, margin: 0 }}>
            碎片聚合 — AI Agent 观点分析
          </Title>
        </Col>
        <Col>
          <Select
            value={target}
            onChange={setTarget}
            options={targetOptions}
            style={{ width: 160 }}
            popupMatchSelectWidth={false}
          />
        </Col>
      </Row>

      {/* ── 共识信息行 ── */}
      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
          marginBottom: 24,
        }}
        styles={{ body: { padding: "16px 24px" } }}
      >
        <Row align="middle" gutter={24}>
          <Col>
            <Text strong style={{ color: colors.muted, fontSize: 13 }}>
              共识操作
            </Text>
            <div style={{ marginTop: 4 }}>
              <Tag
                color={actionConfig[consensusAction].color}
                icon={actionConfig[consensusAction].icon}
                style={{ fontSize: 14, padding: "2px 12px" }}
              >
                {actionConfig[consensusAction].label}
              </Tag>
            </div>
          </Col>
          <Col>
            <Text strong style={{ color: colors.muted, fontSize: 13 }}>
              标的
            </Text>
            <div style={{ marginTop: 4 }}>
              <Text style={{ color: colors.text, fontSize: 16, fontWeight: 600 }}>
                {stockName}
              </Text>
            </div>
          </Col>
          <Col>
            <Text strong style={{ color: colors.muted, fontSize: 13 }}>
              共识分
            </Text>
            <div style={{ marginTop: 4 }}>
              <Text style={{ color: colors.gold, fontSize: 20, fontWeight: 700 }}>
                {consensusScore}
              </Text>
            </div>
          </Col>
          <Col>
            <Text strong style={{ color: colors.muted, fontSize: 13 }}>
              辩论轮次
            </Text>
            <div style={{ marginTop: 4 }}>
              <Text style={{ color: colors.shard, fontSize: 16, fontWeight: 600 }}>
                第 {currentRound} 轮
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      {/* ── Agent 观点卡片 2x2 ── */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        Agent 观点
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {mockOpinions.map((op) => {
          return (
            <Col xs={24} sm={12} key={op.agentId}>
              <Card
                style={{
                  background: colors.card,
                  borderColor: colors.border,
                  height: "100%",
                }}
                styles={{
                  body: { padding: 20 },
                }}
              >
                {/* Agent 名称 */}
                <Row align="middle" justify="space-between" style={{ marginBottom: 12 }}>
                  <Col>
                    <Text
                      strong
                      style={{ color: colors.text, fontSize: 15 }}
                    >
                      {op.agentName}
                    </Text>
                  </Col>
                  <Col>{actionTag(op.action)}</Col>
                </Row>

                {/* 理由 */}
                <Paragraph
                  style={{ color: colors.text, marginBottom: 8, fontSize: 13, lineHeight: 1.6 }}
                >
                  {op.reason}
                </Paragraph>

                {/* 置信度 */}
                <Row align="middle" justify="space-between">
                  <Col>
                    <Text style={{ color: colors.muted, fontSize: 12 }}>
                      置信度
                    </Text>
                  </Col>
                  <Col>
                    <Text
                      style={{
                        color:
                          op.confidence >= 80
                            ? colors.success
                            : op.confidence >= 60
                              ? colors.amber
                              : colors.danger,
                        fontWeight: 600,
                        fontSize: 15,
                      }}
                    >
                      {op.confidence}/100
                    </Text>
                  </Col>
                </Row>

                {/* 证伪理由 */}
                {op.refuteReason && (
                  <div style={{ marginTop: 8 }}>
                    <Text
                      style={{
                        color: colors.dimmed,
                        fontStyle: "italic",
                        fontSize: 12,
                      }}
                    >
                      ⚠ {op.refuteReason}
                    </Text>
                  </div>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* ── Agent 权重列表 ── */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        Agent 权重
      </Title>
      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
        }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={mockWeights}
          columns={weightColumns}
          rowKey="agentId"
          pagination={false}
          style={{ background: "transparent" }}
          components={{
            header: {
              cell: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => (
                <th
                  {...props}
                  style={{
                    ...(props.style || {}),
                    background: colors.surface,
                    color: colors.muted,
                    borderBottom: `1px solid ${colors.border}`,
                  }}
                />
              ),
            },
            body: {
              row: (props: React.HTMLAttributes<HTMLTableRowElement>) => (
                <tr
                  {...props}
                  style={{
                    ...(props.style || {}),
                    background: "transparent",
                  }}
                />
              ),
              cell: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => (
                <td
                  {...props}
                  style={{
                    ...(props.style || {}),
                    background: "transparent",
                    borderBottom: `1px solid ${colors.border}`,
                  }}
                />
              ),
            },
          }}
        />
      </Card>
    </div>
  );
};

export default AgentDiscussionPage;
