import { Card, Typography, Statistic, Row, Col } from "antd";
import {
  ThunderboltOutlined,
  RiseOutlined,
  SafetyOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

const DashboardPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        宇宙总览
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>市场状态</span>}
              value="非主线状态"
              prefix={<ThunderboltOutlined style={{ color: colors.nebula }} />}
              valueStyle={{ color: colors.amber, fontSize: 20 }}
            />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: colors.muted, fontSize: 12 }}>
                仓位建议：0%
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>总资产</span>}
              value="--"
              prefix="¥"
              valueStyle={{ color: colors.text, fontSize: 20 }}
            />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: colors.muted, fontSize: 12 }}>
                今日盈亏：--
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>策略候选</span>}
              value={0}
              prefix={<RiseOutlined style={{ color: colors.gold }} />}
              valueStyle={{ color: colors.text, fontSize: 20 }}
              suffix="只"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>风控事件</span>}
              value={0}
              prefix={<SafetyOutlined style={{ color: colors.success }} />}
              valueStyle={{ color: colors.text, fontSize: 20 }}
              suffix="条"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="最近交易">
            <div style={{ padding: 40, textAlign: "center" }}>
              <Text style={{ color: colors.muted }}>暂无交易数据</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="股票池概览">
            <div style={{ padding: 40, textAlign: "center" }}>
              <Text style={{ color: colors.muted }}>暂无候选数据</Text>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="最新风控事件">
            <div style={{ padding: 40, textAlign: "center" }}>
              <Text style={{ color: colors.muted }}>暂无风控事件</Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DashboardPage;
