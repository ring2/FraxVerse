import { useEffect, useState } from "react";
import { App, Card, Select, Tag, Typography, Row, Col, Table, Spin } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { agentService } from "../../services/agentService";
import type { AgentDiscussionItem, AgentWeightItem } from "../../types/api-extended";

const { Title, Text, Paragraph } = Typography;

// ─── Mock Data (fallback) — TODO: remove once API returns real data ──────────

const fallbackDiscussions: AgentDiscussionItem[] = [];
const fallbackWeights: AgentWeightItem[] = [];

// ─── Helpers ─────────────────────────────────────────────────────────────────

// Infer action from discussion: if buy_reasons has content → buy, if against_reasons has content → sell, else hold
function inferAction(disc: AgentDiscussionItem): string {
  const hasBuy = disc.buy_reasons?.length > 0;
  const hasAgainst = disc.against_reasons?.length > 0;
  if (hasBuy && !hasAgainst) return "buy";
  if (!hasBuy && hasAgainst) return "sell";
  if (hasBuy && hasAgainst) return "hold";
  return "hold";
}

function buildReason(disc: AgentDiscussionItem): string {
  const reasons: string[] = [];
  if (disc.buy_reasons?.length) {
    reasons.push(...disc.buy_reasons.slice(0, 1));
  }
  if (disc.against_reasons?.length) {
    reasons.push(...disc.against_reasons.slice(0, 1));
  }
  return reasons.join("；") || "暂无观点";
}

function buildRefute(disc: AgentDiscussionItem): string | undefined {
  if (disc.against_reasons?.length > 1) {
    return disc.against_reasons.slice(1).join("；");
  }
  if (disc.buy_reasons?.length > 1 && disc.against_reasons?.length > 0) {
    return disc.against_reasons[0];
  }
  return undefined;
}

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
  const cfg = actionConfig[action] ?? actionConfig.hold;
  return (
    <Tag color={cfg.color} icon={cfg.icon}>
      {cfg.label}
    </Tag>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────

const AgentDiscussionPage: React.FC = () => {
  const { message } = App.useApp();
  const [discussions, setDiscussions] = useState<AgentDiscussionItem[]>([]);
  const [weights, setWeights] = useState<AgentWeightItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      agentService.getDiscussions(),
      agentService.getWeights(),
    ])
      .then(([discs, wts]) => {
        setDiscussions(discs);
        setWeights(wts);
      })
      .catch((err) => {
        console.error("Failed to load agent discussion data:", err);
        message.error("加载Agent数据失败，使用演示数据");
      })
      .finally(() => setLoading(false));
  }, []);

  // Derive target options from discussion stock codes
  const stockCodes = Array.from(new Set(discussions.map((d) => d.stock_code)));
  const targetOptions = stockCodes.map((code) => ({
    value: code,
    label: code,
  }));
  const defaultTarget = targetOptions[0]?.value ?? "贵州茅台";
  const [target, setTarget] = useState<string>(defaultTarget);

  // Filter discussions for selected stock, group by agent_name, take latest per agent
  const filteredDiscs = discussions
    .filter((d) => d.stock_code === target)
    .reduce<Map<string, AgentDiscussionItem>>((acc, d) => {
      const existing = acc.get(d.agent_name);
      if (!existing || d.round_num > existing.round_num) {
        acc.set(d.agent_name, d);
      }
      return acc;
    }, new Map());

  const opinions = Array.from(filteredDiscs.values());

  // Compute consensus info from opinions
  const consensusScore = opinions.length > 0
    ? Math.round(opinions.reduce((s, o) => s + (o.score ?? 0), 0) / opinions.length)
    : 0;
  const consensusAction = opinions.length > 0
    ? (opinions.some((o) => inferAction(o) === "buy") ? "buy" : opinions.some((o) => inferAction(o) === "sell") ? "sell" : "hold")
    : "hold";
  const currentRound = opinions.length > 0
    ? Math.max(...opinions.map((o) => o.round_num))
    : 0;

  const weightColumns = [
    {
      title: "Agent",
      dataIndex: "agent_name",
      key: "agent_name",
      render: (v: string) => (
        <span style={{ color: colors.text }}>{v}</span>
      ),
    },
    {
      title: "基础权重",
      dataIndex: "base_weight",
      key: "base_weight",
      render: (v: number) => (
        <span style={{ color: colors.gold }}>{(v * 100).toFixed(0)}%</span>
      ),
    },
    {
      title: "有效权重",
      dataIndex: "effective_weight",
      key: "effective_weight",
      render: (v: number) => (
        <span style={{ color: colors.shard }}>{(v * 100).toFixed(0)}%</span>
      ),
    },
    {
      title: "胜率",
      dataIndex: "win_rate",
      key: "win_rate",
      render: (v: number | null | undefined) => (
        <span style={{ color: colors.shard }}>
          {v != null ? `${(v * 100).toFixed(1)}%` : "-"}
        </span>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  const items = discussions.length > 0 ? discussions : fallbackDiscussions;
  const weightItems = weights.length > 0 ? weights : fallbackWeights;
  const hasData = items.length > 0;

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
            options={targetOptions.length > 0 ? targetOptions : [{ value: "贵州茅台", label: "贵州茅台" }]}
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
                color={actionConfig[consensusAction]?.color ?? colors.amber}
                icon={actionConfig[consensusAction]?.icon ?? <MinusCircleOutlined />}
                style={{ fontSize: 14, padding: "2px 12px" }}
              >
                {actionConfig[consensusAction]?.label ?? "持有"}
              </Tag>
            </div>
          </Col>
          <Col>
            <Text strong style={{ color: colors.muted, fontSize: 13 }}>
              标的
            </Text>
            <div style={{ marginTop: 4 }}>
              <Text style={{ color: colors.text, fontSize: 16, fontWeight: 600 }}>
                {target}
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
      {!hasData ? (
        <div style={{ textAlign: "center", paddingTop: 40, color: colors.dimmed }}>
          暂无讨论数据
        </div>
      ) : opinions.length === 0 ? (
        <div style={{ textAlign: "center", paddingTop: 40, color: colors.dimmed }}>
          该标的暂无讨论数据
        </div>
      ) : (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {opinions.map((op) => {
            const action = inferAction(op);
            const reason = buildReason(op);
            const refute = buildRefute(op);
            const confidence = op.confidence ?? 50;

            return (
              <Col xs={24} sm={12} key={`${op.agent_name}-${op.round_num}`}>
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
                      <Text strong style={{ color: colors.text, fontSize: 15 }}>
                        {op.agent_name}
                      </Text>
                    </Col>
                    <Col>{actionTag(action)}</Col>
                  </Row>

                  {/* 理由 */}
                  <Paragraph
                    style={{ color: colors.text, marginBottom: 8, fontSize: 13, lineHeight: 1.6 }}
                  >
                    {reason}
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
                            confidence >= 80
                              ? colors.success
                              : confidence >= 60
                                ? colors.amber
                                : colors.danger,
                          fontWeight: 600,
                          fontSize: 15,
                        }}
                      >
                        {confidence}/100
                      </Text>
                    </Col>
                  </Row>

                  {/* 证伪理由 */}
                  {refute && (
                    <div style={{ marginTop: 8 }}>
                      <Text
                        style={{
                          color: colors.dimmed,
                          fontStyle: "italic",
                          fontSize: 12,
                        }}
                      >
                        ⚠ {refute}
                      </Text>
                    </div>
                  )}
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

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
          dataSource={weightItems}
          columns={weightColumns}
          rowKey="agent_name"
          pagination={false}
          style={{ background: "transparent" }}
          locale={{ emptyText: "暂无权重数据" }}
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
