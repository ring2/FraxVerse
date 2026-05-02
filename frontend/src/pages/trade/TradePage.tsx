import { Card, Typography } from "antd";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

const TradePage: React.FC = () => (
  <div>
    <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
      交易星图
    </Title>
    <Card>
      <div style={{ padding: 40, textAlign: "center" }}>
        <Text style={{ color: colors.muted }}>交易持仓将在此展示</Text>
      </div>
    </Card>
  </div>
);

export default TradePage;
