import { Card, Typography, List, Tag, Space } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  BellOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";

const { Title, Text } = Typography;

// ─── Mock Data ───────────────────────────────────────────────────────────────

interface Notification {
  id: string;
  time: string;
  type: "trade" | "stop_loss" | "alert" | "system";
  title: string;
  content: string;
}

const mockNotifications: Notification[] = [
  {
    id: "1",
    time: "2026-04-29 14:35:22",
    type: "trade",
    title: "成交通知",
    content: "贵州茅台（600519）买入1200股，成交价185.50元，成交金额222,600元。",
  },
  {
    id: "2",
    time: "2026-04-29 14:30:00",
    type: "stop_loss",
    title: "止损触发",
    content: "宁德时代（300750）触及止损位68.00元，已自动平仓3500股。",
  },
  {
    id: "3",
    time: "2026-04-29 13:45:10",
    type: "alert",
    title: "预警提醒",
    content: "中国平安（601318）盘中跌幅超过3%，当前价格51.02元/股。",
  },
  {
    id: "4",
    time: "2026-04-29 12:00:15",
    type: "system",
    title: "系统通知",
    content: "行情源连接超时，已自动重连成功，期间数据已补全。",
  },
  {
    id: "5",
    time: "2026-04-29 10:22:08",
    type: "trade",
    title: "成交通知",
    content: "五粮液（000858）买入800股，成交价142.30元，成交金额113,840元。",
  },
  {
    id: "6",
    time: "2026-04-29 09:45:33",
    type: "alert",
    title: "预警提醒",
    content: "招商银行（600036）MACD金叉信号出现，建议关注。",
  },
  {
    id: "7",
    time: "2026-04-28 15:30:00",
    type: "system",
    title: "系统通知",
    content: "日终清算完成，今日交易数据已归档。",
  },
  {
    id: "8",
    time: "2026-04-28 14:50:12",
    type: "trade",
    title: "成交通知",
    content: "迈瑞医疗（300760）买入600股，成交价268.50元，成交金额161,100元。",
  },
  {
    id: "9",
    time: "2026-04-28 13:20:45",
    type: "stop_loss",
    title: "止损触发",
    content: "隆基绿能（601012）触及止损位28.00元，已自动平仓10000股。",
  },
  {
    id: "10",
    time: "2026-04-28 09:35:00",
    type: "system",
    title: "系统通知",
    content: "数据采集模块启动完成，K线数据、板块数据、资金流数据同步正常。",
  },
];

// ─── Config ───────────────────────────────────────────────────────────────────

const typeConfig: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  trade: {
    color: colors.shard,
    icon: <CheckCircleOutlined />,
    label: "成交",
  },
  stop_loss: {
    color: colors.danger,
    icon: <CloseCircleOutlined />,
    label: "止损",
  },
  alert: {
    color: colors.amber,
    icon: <WarningOutlined />,
    label: "预警",
  },
  system: {
    color: colors.nebula,
    icon: <BellOutlined />,
    label: "系统",
  },
};

// ─── Component ───────────────────────────────────────────────────────────────

const NotificationPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ color: colors.text, marginBottom: 24 }}>
        回音 — 消息通知
      </Title>

      <Card
        style={{
          background: colors.card,
          borderColor: colors.border,
          borderRadius: 8,
        }}
        styles={{ body: { padding: "12px 20px" } }}
      >
        <List
          dataSource={mockNotifications}
          renderItem={(item) => {
            const cfg = typeConfig[item.type];
            return (
              <List.Item
                style={{
                  borderBottom: `1px solid ${colors.border}`,
                  padding: "14px 0",
                }}
              >
                <List.Item.Meta
                  avatar={
                    <Tag
                      icon={cfg.icon}
                      color={cfg.color}
                      style={{ borderRadius: 4, margin: 0, whiteSpace: "nowrap" }}
                    >
                      {cfg.label}
                    </Tag>
                  }
                  title={
                    <Space size={12}>
                      <Text style={{ color: colors.text, fontWeight: 500, fontSize: 14 }}>
                        {item.title}
                      </Text>
                      <Text style={{ color: colors.dimmed, fontSize: 12 }}>
                        {item.time}
                      </Text>
                    </Space>
                  }
                  description={
                    <Text style={{ color: colors.muted, fontSize: 13, lineHeight: 1.6 }}>
                      {item.content}
                    </Text>
                  }
                />
              </List.Item>
            );
          }}
        />
      </Card>
    </div>
  );
};

export default NotificationPage;
