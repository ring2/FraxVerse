import { useEffect, useState } from "react";
import { Row, Col, Card, Typography, Tag, Space, Spin } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import api from "../../services/api";
import type { ExperienceItem } from "../../types/api-extended";

const { Title, Text, Paragraph } = Typography;

// ─── Field Mapping ───────────────────────────────────────────────────────────

function mapOperation(op: string): string {
  const m: Record<string, string> = {
    buy: "买入",
    sell: "卖出",
    hold: "持有",
  };
  return m[op] ?? op;
}

function mapResult(result: string): "success" | "fail" {
  if (result === "success" || result === "成功") return "success";
  return "fail";
}

function buildSummary(exp: ExperienceItem): string {
  // Use tags as summary content if available, otherwise build from fields
  const tags = exp.tags?.length ? exp.tags.join("、") : "";
  const pnlInfo = exp.pnl_pct ? `盈亏: ${exp.pnl_pct}%` : "";
  const scoreInfo = exp.score ? `评分: ${exp.score}` : "";
  const parts = [tags, pnlInfo, scoreInfo].filter(Boolean);
  return parts.length > 0 ? parts.join(" | ") : `${exp.operation} · ${exp.result}`;
}

// ─── Component ───────────────────────────────────────────────────────────────

const ExperiencePage: React.FC = () => {
  const [experiences, setExperiences] = useState<ExperienceItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .get("/experience/list")
      .then((res) => {
        if (!cancelled) {
          const data = Array.isArray(res.data) ? res.data : [];
          setExperiences(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("获取经验数据失败:", err);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  const items = experiences;

  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        内观 — 历史经验
      </Title>

      {items.length === 0 ? (
        <div style={{ textAlign: "center", paddingTop: 40, color: colors.dimmed }}>
          <Text style={{ color: colors.dimmed, fontSize: 13 }}>暂无经验数据——完成交易后经验将自动沉淀</Text>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          {items.map((exp) => {
            const resultType = mapResult(exp.result);
            const actionLabel = mapOperation(exp.operation);
            const summary = buildSummary(exp);

            return (
              <Col xs={24} sm={12} lg={8} key={exp.id}>
                <Card
                  style={{
                    background: colors.card,
                    borderColor: colors.border,
                    borderRadius: 8,
                    height: "100%",
                  }}
                  styles={{ body: { padding: 20 } }}
                >
                  {/* 顶部：日期 + 结果标签 */}
                  <Row align="middle" justify="space-between" style={{ marginBottom: 12 }}>
                    <Col>
                      <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                        {exp.created_at?.slice(0, 10) ?? "-"}
                      </Text>
                    </Col>
                    <Col>
                      <Tag
                        icon={
                          resultType === "success" ? (
                            <CheckCircleOutlined />
                          ) : (
                            <CloseCircleOutlined />
                          )
                        }
                        color={resultType === "success" ? colors.success : colors.danger}
                        style={{ borderRadius: 4, margin: 0 }}
                      >
                        {resultType === "success" ? "成功" : "失败"}
                      </Tag>
                    </Col>
                  </Row>

                  {/* 标的 / 策略类型 */}
                  <Space size={6} style={{ marginBottom: 8 }}>
                    <Text style={{ color: colors.text, fontWeight: 600, fontSize: 15 }}>
                      {exp.strategy_type ?? "-"}
                    </Text>
                    <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                      {exp.market_state ?? ""}
                    </Text>
                  </Space>

                  {/* 操作标签 */}
                  <div style={{ marginBottom: 12 }}>
                    <Tag
                      color={actionLabel === "买入" ? colors.danger : colors.success}
                      style={{ borderRadius: 4 }}
                    >
                      {actionLabel}
                    </Tag>
                  </div>

                  {/* 心得摘要 */}
                  <Paragraph
                    style={{
                      color: colors.muted,
                      fontSize: 13,
                      lineHeight: 1.7,
                      marginBottom: 0,
                    }}
                  >
                    {summary}
                  </Paragraph>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
};

export default ExperiencePage;
