import { useEffect, useState, useCallback } from "react";
import { App, Card, Select, Tag, Typography, Row, Col, Table, Spin, Button, Space, Divider, Statistic, Badge, Modal, Alert } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  WarningOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { agentService } from "../../services/agentService";
import type { AgentDiscussionItemEx, AgentWeightItemEx, AgentDecisionItemEx } from "../../services/agentService";

const { Title, Text } = Typography;

// ─── Agent 显示名称映射 ─────────────────────────────────────────────────────────

const AGENT_DISPLAY: Record<string, { label: string; color: string }> = {
  mainline_hunter: { label: "主线猎手", color: "#d4380d" },
  fund_detective: { label: "资金侦探", color: "#096dd9" },
  sentiment_catcher: { label: "情绪捕手", color: "#7cb305" },
  experience_judge: { label: "经验法官", color: "#722ed1" },
};

// ─── 辅助函数 ────────────────────────────────────────────────────────────────────

function actionConfig(action: string) {
  const map: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    buy: { color: colors.danger, icon: <CheckCircleOutlined />, label: "买入" },
    sell: { color: colors.success, icon: <CloseCircleOutlined />, label: "卖出" },
    reject: { color: colors.dimmed, icon: <CloseCircleOutlined />, label: "否决" },
    hold: { color: colors.amber, icon: <MinusCircleOutlined />, label: "持有" },
  };
  return map[action] ?? map.hold;
}

function confidenceColor(score: number | null) {
  if (score == null) return colors.dimmed;
  if (score >= 80) return colors.success;
  if (score >= 60) return colors.amber;
  return colors.danger;
}

// ─── 权重表格列 ──────────────────────────────────────────────────────────────────

const weightColumns = [
  {
    title: "Agent",
    dataIndex: "agentName",
    key: "agentName",
    render: (v: string) => {
      const info = AGENT_DISPLAY[v];
      return <span style={{ color: colors.text }}>{info?.label ?? v}</span>;
    },
  },
  {
    title: "市场状态",
    dataIndex: "marketState",
    key: "marketState",
    render: (v: string) => (
      <Tag color={v === "mainline_confirmed" ? "blue" : "orange"} style={{ fontSize: 11 }}>
        {v === "mainline_confirmed" ? "主线确认" : v === "oscillating" ? "震荡市" : v}
      </Tag>
    ),
  },
  {
    title: "基准权重",
    dataIndex: "baseWeight",
    key: "baseWeight",
    render: (v: number) => <span style={{ color: colors.gold }}>{(v * 100).toFixed(0)}%</span>,
  },
  {
    title: "校准系数",
    dataIndex: "calibFactor",
    key: "calibFactor",
    render: (v: number) => {
      const color = v > 1 ? colors.success : v < 0.8 ? colors.danger : colors.amber;
      return <span style={{ color }}>{v.toFixed(2)}x</span>;
    },
  },
  {
    title: "有效权重",
    dataIndex: "effectiveWeight",
    key: "effectiveWeight",
    render: (v: number) => <span style={{ color: colors.shard }}>{(v * 100).toFixed(0)}%</span>,
  },
  {
    title: "胜率",
    dataIndex: "winRate",
    key: "winRate",
    render: (v: number | null | undefined) => {
      const val = v ?? 0.5;
      const color = val >= 0.6 ? colors.success : val >= 0.4 ? colors.amber : colors.danger;
      return <span style={{ color }}>{(val * 100).toFixed(1)}%</span>;
    },
  },
  {
    title: "样本",
    dataIndex: "recentCount",
    key: "recentCount",
    render: (v: number) => <span style={{ color: colors.muted }}>{v}</span>,
  },
  {
    title: "状态",
    dataIndex: "isDegraded",
    key: "isDegraded",
    render: (v: boolean) => v
      ? <Tag color="red" icon={<WarningOutlined />}>已降级</Tag>
      : <Tag color="green">正常</Tag>,
  },
];

// ─── 决策表格列 ──────────────────────────────────────────────────────────────────

const decisionColumns = [
  {
    title: "标的",
    dataIndex: "stockCode",
    key: "stockCode",
    render: (v: string) => <span style={{ color: colors.text, fontWeight: 600 }}>{v}</span>,
  },
  {
    title: "决策",
    dataIndex: "decision",
    key: "decision",
    render: (v: string) => {
      const cfg = actionConfig(v);
      return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>;
    },
  },
  {
    title: "总分",
    dataIndex: "totalScore",
    key: "totalScore",
    render: (v: number) => <span style={{ color: colors.gold, fontWeight: 600 }}>{v.toFixed(1)}</span>,
  },
  {
    title: "净分",
    dataIndex: "netScore",
    key: "netScore",
    render: (v: number) => {
      const color = v > 0 ? colors.success : colors.danger;
      return <span style={{ color }}>{(v > 0 ? "+" : "")}{v.toFixed(1)}</span>;
    },
  },
  {
    title: "风控",
    dataIndex: "riskVeto",
    key: "riskVeto",
    render: (v: boolean) => v ? <Tag color="red" icon={<CloseCircleOutlined />}>否决</Tag> : <Tag color="green">通过</Tag>,
  },
  {
    title: "收敛方式",
    dataIndex: "convergenceMethod",
    key: "convergenceMethod",
    render: (v: string) => {
      const methodLabels: Record<string, string> = {
        normal: "正常",
        trimmed_mean: "修剪均值",
        degraded_rule: "纯规则",
        degraded_single: "替补",
      };
      return <Tag color={v.includes("degraded") ? "orange" : "blue"}>{methodLabels[v] ?? v}</Tag>;
    },
  },
];

// ─── Component ───────────────────────────────────────────────────────────────────

const AgentDiscussionPage: React.FC = () => {
  const { message } = App.useApp();
  const [discussions, setDiscussions] = useState<AgentDiscussionItemEx[]>([]);
  const [weights, setWeights] = useState<AgentWeightItemEx[]>([]);
  const [decisions, setDecisions] = useState<AgentDecisionItemEx[]>([]);
  const [currentMarketState, setCurrentMarketState] = useState("mainline_confirmed");
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [discResult, wtResult, decResult] = await Promise.all([
        agentService.getDiscussions({ pageSize: 100 }),
        agentService.getWeights(),
        agentService.getDecisions(),
      ]);
      setDiscussions(discResult.items);
      setWeights(wtResult.weights);
      setDecisions(decResult.decisions);
      setCurrentMarketState(wtResult.currentMarketState);
    } catch (err) {
      console.error("Failed to load agent data:", err);
      message.error("加载Agent数据失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ─── 手动触发分析 ──────────────────────────────────────────────────────────────
  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerResult, setTriggerResult] = useState<{
    success: boolean;
    stockCount: number;
    decisions: Array<{ stockCode: string; decision: string; totalScore: number }>;
  } | null>(null);
  const [selectedTriggerCodes, setSelectedTriggerCodes] = useState<string[]>([]);

  const handleTrigger = useCallback(async () => {
    setTriggerLoading(true);
    setTriggerResult(null);
    try {
      const result = await agentService.triggerAnalysis(
        selectedTriggerCodes.length > 0 ? selectedTriggerCodes : undefined
      );
      setTriggerResult({
        success: true,
        stockCount: result.stockCount,
        decisions: result.decisions,
      });
      // 分析完成后自动刷新数据
      setTimeout(() => {
        loadData();
      }, 1000);
    } catch (err) {
      console.error("Trigger analysis failed:", err);
      setTriggerResult({ success: false, stockCount: 0, decisions: [] });
    } finally {
      setTriggerLoading(false);
    }
  }, [selectedTriggerCodes, loadData]);

  // 标的筛选
  const stockCodes = Array.from(new Set(discussions.map(d => d.stockCode)));
  const targetOptions = stockCodes.map(code => ({ value: code, label: code }));
  const [target, setTarget] = useState<string>("");
  useEffect(() => {
    if (targetOptions.length > 0 && !target) {
      setTarget(targetOptions[0].value);
    }
  }, [targetOptions, target]);

  // 按标的过滤讨论
  const filteredDiscs = discussions
    .filter(d => d.stockCode === target)
    .reduce<Map<string, AgentDiscussionItemEx>>((acc, d) => {
      const key = d.agentName;
      const existing = acc.get(key);
      if (!existing || d.roundNum > existing.roundNum) {
        acc.set(key, d);
      }
      return acc;
    }, new Map());

  const opinions = Array.from(filteredDiscs.values());

  // 共识信息
  const consensusScore = opinions.length > 0
    ? Math.round(opinions.reduce((s, o) => s + (o.score ?? 0), 0) / opinions.length)
    : 0;
  const buyCount = opinions.filter(o => o.predictedOutcome === "buy").length;
  const currentRound = opinions.length > 0
    ? Math.max(...opinions.map(o => o.roundNum))
    : 0;

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {/* ── 标题行 ── */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ color: colors.text, margin: 0 }}>
            <ExperimentOutlined style={{ marginRight: 8, color: colors.shard }} />
            碎片聚合 — AI Agent 观点分析
          </Title>
        </Col>
        <Col>
          <Space>
            <Badge
              status={currentMarketState === "mainline_confirmed" ? "success" : "warning"}
              text={
                <Text style={{ color: colors.muted, fontSize: 13 }}>
                  市场状态: {currentMarketState === "mainline_confirmed" ? "主线确认" : currentMarketState === "oscillating" ? "震荡市" : currentMarketState === "extreme" ? "极端行情" : currentMarketState}
                </Text>
              }
            />
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleTrigger}
              loading={triggerLoading}
              size="small"
            >
              触发分析
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadData} size="small">
              刷新
            </Button>
          </Space>
        </Col>
      </Row>

      {/* ── 标的选择 ── */}
      <Row style={{ marginBottom: 16 }}>
        <Col>
          <Select
            value={target || undefined}
            onChange={setTarget}
            options={targetOptions.length > 0 ? targetOptions : [{ value: "暂无", label: "暂无数据" }]}
            style={{ width: 200 }}
            placeholder="选择标的"
          />
        </Col>
      </Row>

      {/* ── 共识信息行 ── */}
      <Card
        style={{ background: colors.card, borderColor: colors.border, marginBottom: 24 }}
        styles={{ body: { padding: "16px 24px" } }}
      >
        <Row gutter={[32, 12]}>
          <Col>
            <Statistic
              title={<span style={{ color: colors.muted }}>共识评分</span>}
              value={consensusScore}
              suffix="/100"
              valueStyle={{ color: colors.gold, fontWeight: 700 }}
            />
          </Col>
          <Col>
            <Statistic
              title={<span style={{ color: colors.muted }}>推荐买入</span>}
              value={buyCount}
              suffix={`/ ${opinions.length}`}
              valueStyle={{ color: colors.danger }}
            />
          </Col>
          <Col>
            <Statistic
              title={<span style={{ color: colors.muted }}>辩论轮次</span>}
              value={currentRound}
              suffix="轮"
              valueStyle={{ color: colors.shard }}
            />
          </Col>
        </Row>
      </Card>

      {/* ── Agent 观点卡片 2x2 ── */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        <ThunderboltOutlined style={{ marginRight: 6 }} />
        Agent 观点
      </Title>

      {opinions.length === 0 ? (
        <div style={{ textAlign: "center", paddingTop: 40, color: colors.dimmed }}>
          <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无讨论数据——请先触发 Agent 分析</Text>
        </div>
      ) : (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {opinions.map((op) => {
            const info = AGENT_DISPLAY[op.agentName] ?? { label: op.agentName, color: colors.shard };
            const action = op.predictedOutcome ?? "hold";
            const cfg = actionConfig(action);

            return (
              <Col xs={24} sm={12} key={`${op.agentName}-${op.roundNum}`}>
                <Card
                  style={{ background: colors.card, borderColor: colors.border, height: "100%", borderLeft: `3px solid ${info.color}` }}
                  styles={{ body: { padding: 20 } }}
                >
                  {/* Agent 名称 + 操作 */}
                  <Row align="middle" justify="space-between" style={{ marginBottom: 10 }}>
                    <Col>
                      <Space>
                        <Text strong style={{ color: colors.text, fontSize: 15 }}>
                          {info.label}
                        </Text>
                        <Text style={{ color: colors.dimmed, fontSize: 11 }}>
                          {op.agentName}
                        </Text>
                      </Space>
                    </Col>
                    <Col>
                      <Tag color={cfg.color} icon={cfg.icon} style={{ fontSize: 12 }}>
                        {cfg.label}
                      </Tag>
                    </Col>
                  </Row>

                  {/* 评分 + 信心度 */}
                  <Row align="middle" gutter={16} style={{ marginBottom: 10 }}>
                    <Col>
                      <Space align="center" size={4}>
                        <Text style={{ color: colors.muted, fontSize: 12 }}>评分</Text>
                        <Text style={{ color: colors.gold, fontSize: 22, fontWeight: 700 }}>
                          {op.score ?? "-"}
                        </Text>
                      </Space>
                    </Col>
                    <Col>
                      <Space align="center" size={4}>
                        <Text style={{ color: colors.muted, fontSize: 12 }}>信心</Text>
                        <Text style={{ color: confidenceColor(op.confidence), fontSize: 16, fontWeight: 600 }}>
                          {op.confidence ? `${(op.confidence * 100).toFixed(0)}%` : "-"}
                        </Text>
                      </Space>
                    </Col>
                  </Row>

                  {/* 买入理由 */}
                  <div style={{ marginBottom: 8 }}>
                    <Text style={{ color: colors.success, fontSize: 12, fontWeight: 600 }}>📈 买入理由</Text>
                    {op.buyReasons.length > 0 ? (
                      <ul style={{ margin: "4px 0 0 0", paddingLeft: 16, color: colors.text, fontSize: 13, lineHeight: 1.7 }}>
                        {op.buyReasons.slice(0, 2).map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    ) : (
                      <Text style={{ color: colors.dimmed, fontSize: 12, marginLeft: 16 }}>无</Text>
                    )}
                  </div>

                  {/* 反对理由（证伪） */}
                  <div>
                    <Text style={{ color: colors.danger, fontSize: 12, fontWeight: 600 }}>📉 反对理由</Text>
                    {op.againstReasons.length > 0 ? (
                      <ul style={{ margin: "4px 0 0 0", paddingLeft: 16, color: colors.dimmed, fontSize: 13, lineHeight: 1.7, fontStyle: "italic" }}>
                        {op.againstReasons.slice(0, 2).map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    ) : (
                      <Text style={{ color: colors.dimmed, fontSize: 12, marginLeft: 16 }}>无（评分已降）</Text>
                    )}
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {/* ── 手动触发 Agent 分析 ── */}
      <Card
        style={{ background: colors.surface, borderColor: colors.border, borderStyle: "dashed", marginBottom: 24 }}
        styles={{ body: { padding: "16px 24px" } }}
      >
        <Row align="middle" justify="space-between">
          <Col>
            <Space>
              <PlayCircleOutlined style={{ color: colors.shard, fontSize: 20 }} />
              <div>
                <Text strong style={{ color: colors.text, display: "block" }}>
                  手动触发 Agent 分析
                </Text>
                <Text style={{ color: colors.muted, fontSize: 12 }}>
                  将使用当前市场状态和股票池数据，触发完整的 Agent 辩论→投票→决策流程
                </Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                setTriggerModalOpen(true);
                setTriggerResult(null);
                setSelectedTriggerCodes([]);
              }}
              style={{ background: colors.shard, borderColor: colors.shard }}
            >
              开始分析
            </Button>
          </Col>
        </Row>

        {/* 触发结果展示 */}
        {triggerResult && (
          <div style={{ marginTop: 12, padding: 12, background: colors.card, borderRadius: 6 }}>
            {triggerResult.success ? (
              <Space direction="vertical" style={{ width: "100%" }}>
                <Alert
                  type="success"
                  message={`分析完成 — 涉及 ${triggerResult.stockCount} 只标的`}
                  showIcon
                  style={{ background: "rgba(82, 196, 26, 0.1)", border: "none", color: colors.text }}
                />
                {triggerResult.decisions.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text style={{ color: colors.muted, fontSize: 12 }}>分析结果：</Text>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
                      {triggerResult.decisions.slice(0, 10).map((d) => {
                        const cfg = actionConfig(d.decision);
                        return (
                          <Tag key={d.stockCode} color={cfg.color}>
                            {d.stockCode}: {cfg.label} ({d.totalScore.toFixed(0)}分)
                          </Tag>
                        );
                      })}
                      {triggerResult.decisions.length > 10 && (
                        <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                          ...共 {triggerResult.decisions.length} 只
                        </Text>
                      )}
                    </div>
                  </div>
                )}
              </Space>
            ) : (
              <Alert type="error" message="分析触发失败，请检查后端服务状态" showIcon />
            )}
          </div>
        )}
      </Card>

      {/* ── 触发分析 Modal ── */}
      <Modal
        title={
          <Space>
            <PlayCircleOutlined style={{ color: colors.shard }} />
            <span>触发 Agent 分析</span>
          </Space>
        }
        open={triggerModalOpen}
        onCancel={() => setTriggerModalOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setTriggerModalOpen(false)}>取消</Button>
            <Button
              type="primary"
              loading={triggerLoading}
              icon={triggerLoading ? <LoadingOutlined /> : <PlayCircleOutlined />}
              onClick={handleTrigger}
              style={{ background: colors.shard, borderColor: colors.shard }}
            >
              {triggerLoading ? "分析中..." : "确认触发"}
            </Button>
          </Space>
        }
        styles={{ content: { background: colors.card }, header: { background: colors.card, borderBottom: `1px solid ${colors.border}` } }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Text style={{ color: colors.muted }}>
            将触发 AI Agent 对以下标的进行完整的辩论→加权投票→决策流程。
          </Text>

          {stockCodes.length > 0 && (
            <>
              <div style={{ marginTop: 8 }}>
                <Text style={{ color: colors.text, display: "block", marginBottom: 8 }}>
                  可选特定标的（留空 = 分析全部）
                </Text>
                <Select
                  mode="multiple"
                  placeholder="选择标的（可选）"
                  value={selectedTriggerCodes}
                  onChange={setSelectedTriggerCodes}
                  options={stockCodes.map((c) => ({ value: c, label: c }))}
                  style={{ width: "100%" }}
                  maxTagCount={5}
                />
              </div>
            </>
          )}

          {/* 分析中的加载状态 */}
          {triggerLoading && (
            <div style={{ textAlign: "center", padding: "24px 0" }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 32, color: colors.shard }} spin />} />
              <div style={{ marginTop: 12 }}>
                <Text style={{ color: colors.muted }}>Agent 辩论进行中（4个Agent × 2-3轮）...</Text>
              </div>
            </div>
          )}
        </Space>
      </Modal>

      <Divider style={{ borderColor: colors.border, margin: "24px 0" }} />

      {/* ── 今日决策列表 ── */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        <BarChartOutlined style={{ marginRight: 6 }} />
        今日决策
      </Title>

      <Card style={{ background: colors.card, borderColor: colors.border, marginBottom: 24 }} styles={{ body: { padding: 0 } }}>
        <Table
          dataSource={decisions}
          columns={decisionColumns}
          rowKey="stockCode"
          pagination={decisions.length > 10 ? { pageSize: 10, size: "small" } : false}
          style={{ background: "transparent" }}
          locale={{ emptyText: "暂无决策数据" }}
          size="small"
          components={{
            header: {
              cell: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => (
                <th {...props} style={{ ...props.style, background: colors.surface, color: colors.muted, borderBottom: `1px solid ${colors.border}` }} />
              ),
            },
            body: {
              row: (props: React.HTMLAttributes<HTMLTableRowElement>) => (
                <tr {...props} style={{ ...props.style, background: "transparent" }} />
              ),
              cell: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => (
                <td {...props} style={{ ...props.style, background: "transparent", borderBottom: `1px solid ${colors.border}` }} />
              ),
            },
          }}
        />
      </Card>

      <Divider style={{ borderColor: colors.border, margin: "24px 0" }} />

      {/* ── Agent 权重表 ── */}
      <Title level={5} style={{ color: colors.muted, marginBottom: 12 }}>
        <SettingOutlined style={{ marginRight: 6 }} />
        Agent 权重配置
      </Title>

      <Card style={{ background: colors.card, borderColor: colors.border }} styles={{ body: { padding: 0 } }}>
        <Table
          dataSource={weights}
          columns={weightColumns}
          rowKey={(r) => `${r.agentName}-${r.marketState}`}
          pagination={false}
          style={{ background: "transparent" }}
          locale={{ emptyText: "暂无权重数据" }}
          size="small"
          components={{
            header: {
              cell: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => (
                <th {...props} style={{ ...props.style, background: colors.surface, color: colors.muted, borderBottom: `1px solid ${colors.border}` }} />
              ),
            },
            body: {
              row: (props: React.HTMLAttributes<HTMLTableRowElement>) => (
                <tr {...props} style={{ ...props.style, background: "transparent" }} />
              ),
              cell: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => (
                <td {...props} style={{ ...props.style, background: "transparent", borderBottom: `1px solid ${colors.border}` }} />
              ),
            },
          }}
        />
      </Card>
    </div>
  );
};

export default AgentDiscussionPage;
