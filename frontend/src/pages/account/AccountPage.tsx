import { Card, Typography } from "antd";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

const AccountPage: React.FC = () => (
  <div>
    <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
      资产星盘
    </Title>
    <Card>
      <div style={{ padding: 40, textAlign: "center" }}>
        <Text style={{ color: colors.muted }}>账户数据将在接入数据后显示</Text>
      </div>
    </Card>
  </div>
);

export default AccountPage;
