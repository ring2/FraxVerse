import { Row, Col, Card, Typography, Tag, Space } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text, Paragraph } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

interface Experience {
  id: string;
  date: string;
  stockName: string;
  stockCode: string;
  action: string;
  result: "success" | "fail";
  summary: string;
}

const mockExperiences: Experience[] = [
  {
    id: "1",
    date: "2026-04-25",
    stockName: "贵州茅台",
    stockCode: "600519",
    action: "买入",
    result: "success",
    summary: "财报季前布局白酒龙头，Q1业绩超预期带动股价突破前高。耐心持有两周获得7%收益，验证了财报驱动策略的有效性。",
  },
  {
    id: "2",
    date: "2026-04-18",
    stockName: "宁德时代",
    stockCode: "300750",
    action: "卖出",
    result: "success",
    summary: "锂电板块连续上涨后出现放量滞涨信号，及时止盈锁定利润。虽然后续仍有小幅上涨，但规避了随后的回调风险。",
  },
  {
    id: "3",
    date: "2026-04-12",
    stockName: "中国平安",
    stockCode: "601318",
    action: "买入",
    result: "fail",
    summary: "保险股受利率下行预期压制，买入后持续阴跌。教训：左侧交易需确认基本面拐点，不能仅因估值低就入场。",
  },
  {
    id: "4",
    date: "2026-04-05",
    stockName: "招商银行",
    stockCode: "600036",
    action: "卖出",
    result: "fail",
    summary: "银行股反弹初期过早离场，错过了后续10%的涨幅。反思：止盈策略过于保守，应根据趋势强度动态调整目标位。",
  },
  {
    id: "5",
    date: "2026-03-28",
    stockName: "迈瑞医疗",
    stockCode: "300760",
    action: "买入",
    result: "success",
    summary: "医疗器械集采政策落地好于预期，利空出尽后资金回流。买入后一周内涨幅达5%，印证了事件驱动型机会的把握逻辑。",
  },
];

// ─── Component ───────────────────────────────────────────────────────────────

const ExperiencePage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        内观 — 历史经验
      </Title>

      <Row gutter={[16, 16]}>
        {mockExperiences.map((exp) => (
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
                    {exp.date}
                  </Text>
                </Col>
                <Col>
                  <Tag
                    icon={
                      exp.result === "success" ? (
                        <CheckCircleOutlined />
                      ) : (
                        <CloseCircleOutlined />
                      )
                    }
                    color={exp.result === "success" ? colors.success : colors.danger}
                    style={{ borderRadius: 4, margin: 0 }}
                  >
                    {exp.result === "success" ? "成功" : "失败"}
                  </Tag>
                </Col>
              </Row>

              {/* 标的 */}
              <Space size={6} style={{ marginBottom: 8 }}>
                <Text style={{ color: colors.text, fontWeight: 600, fontSize: 15 }}>
                  {exp.stockName}
                </Text>
                <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                  {exp.stockCode}
                </Text>
              </Space>

              {/* 操作标签 */}
              <div style={{ marginBottom: 12 }}>
                <Tag
                  color={exp.action === "买入" ? colors.danger : colors.success}
                  style={{ borderRadius: 4 }}
                >
                  {exp.action}
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
                {exp.summary}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default ExperiencePage;
