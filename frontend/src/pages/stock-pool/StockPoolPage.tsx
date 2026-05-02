import { Card, Typography } from "antd";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

const StockPoolPage: React.FC = () => (
  <div>
    <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
      碎片候选
    </Title>
    <Card>
      <div style={{ padding: 40, textAlign: "center" }}>
        <Text style={{ color: colors.muted }}>策略筛选结果将在此展示</Text>
      </div>
    </Card>
  </div>
);

export default StockPoolPage;
