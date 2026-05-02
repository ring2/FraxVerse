import { useEffect, useState } from "react";
import { Card, Typography, Statistic, Row, Col, Spin } from "antd";
import { App } from "antd";
import {
  ThunderboltOutlined,
  RiseOutlined,
  SafetyOutlined,
} from "@ant-design/icons";
import { colors } from "../../theme/colors";
import { portfolioService } from "../../services/portfolioService";
import { tradeService } from "../../services/tradeService";
import { marketService } from "../../services/marketService";
import type { components } from "../../types/api-generated";

type PortfolioSummary = components["schemas"]["PortfolioSummary"];
type TradeModeResponse = components["schemas"]["TradeModeResponse"];
type MarketStateResponse = components["schemas"]["MarketStateResponse"];

const { Title, Text } = Typography;

const styles: Record<string, React.CSSProperties> = {
  body: {
    padding: "16px 24px",
  },
  header: {
    color: colors.text,
    marginBottom: 24,
  },
};

const DashboardPage: React.FC = () => {
  const { message } = App.useApp();

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [mode, setMode] = useState<TradeModeResponse | null>(null);
  const [marketState, setMarketState] = useState<MarketStateResponse | null>(
    null
  );

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [summaryData, modeData, marketData] = await Promise.all([
          portfolioService.getSummary(),
          tradeService.getMode(),
          marketService.getMarketState(),
        ]);
        setSummary(summaryData);
        setMode(modeData);
        setMarketState(marketData);
      } catch (err) {
        console.error("Dashboard data fetch error:", err);
        message.error("加载仪表盘数据失败");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [message]);

  // --- derived display values ---
  const marketLabel = marketState?.current_state ?? "未知";
  const marketConfidence = marketState?.confidence ?? null;
  const mainLineSector = marketState?.main_line_sector ?? null;

  const positionPct = summary?.total_position_pct ?? null;
  const totalAsset = summary?.total_asset ?? null;
  const dailyPnl = summary?.daily_pnl ?? null;

  const emergencyStop = mode?.emergency_stop ?? false;

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={styles.body}>
      <Title level={3} style={styles.header}>
        宇宙总览
      </Title>

      <Row gutter={[16, 16]}>
        {/* 市场状态 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>市场状态</span>}
              value={marketLabel}
              prefix={<ThunderboltOutlined style={{ color: colors.nebula }} />}
              valueStyle={{
                color: marketConfidence !== null && marketConfidence > 0.5
                  ? colors.success
                  : colors.amber,
                fontSize: 20,
              }}
            />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: colors.muted, fontSize: 12 }}>
                主线：{mainLineSector ?? "无"}
                {marketConfidence !== null && (
                  <> · 置信度：{(marketConfidence * 100).toFixed(0)}%</>
                )}
              </Text>
            </div>
          </Card>
        </Col>

        {/* 总资产 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>总资产</span>}
              value={totalAsset ?? "--"}
              prefix="¥"
              valueStyle={{ color: colors.text, fontSize: 20 }}
            />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: colors.muted, fontSize: 12 }}>
                今日盈亏：{dailyPnl ?? "--"}
                {positionPct !== null && (
                  <> · 仓位：{(Number(positionPct) * 100).toFixed(1)}%</>
                )}
              </Text>
            </div>
          </Card>
        </Col>

        {/* 交易模式 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>交易模式</span>}
              value={mode?.current_mode ?? "未知"}
              prefix={<RiseOutlined style={{ color: colors.gold }} />}
              valueStyle={{ color: colors.text, fontSize: 20 }}
            />
            <div style={{ marginTop: 8 }}>
              <Text
                style={{
                  color: emergencyStop ? colors.danger : colors.muted,
                  fontSize: 12,
                }}
              >
                {emergencyStop ? "🛑 紧急停止中" : `确认模式：${mode?.confirm_mode ?? "--"}`}
              </Text>
            </div>
          </Card>
        </Col>

        {/* 风控事件 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<span style={{ color: colors.muted }}>持仓数量</span>}
              value={summary?.position_count ?? 0}
              prefix={<SafetyOutlined style={{ color: colors.success }} />}
              valueStyle={{ color: colors.text, fontSize: 20 }}
              suffix="只"
            />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: colors.muted, fontSize: 12 }}>
                可用资金：¥{summary?.available_cash ?? "--"}
              </Text>
            </div>
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
