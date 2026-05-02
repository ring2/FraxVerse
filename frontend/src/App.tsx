import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import PcLayout from "./components/layout/PcLayout";
import ProtectedRoute from "./components/common/ProtectedRoute";
import LoadingFallback from "./components/common/LoadingFallback";

// Lazy load pages
const LoginPage = lazy(() => import("./pages/login/LoginPage"));
const DashboardPage = lazy(() => import("./pages/dashboard/DashboardPage"));

const AccountPage = lazy(() =>
  import("./pages/account/AccountPage").catch(() => ({
    default: () => <div>账户页面</div>,
  }))
);
const StockPoolPage = lazy(() =>
  import("./pages/stock-pool/StockPoolPage").catch(() => ({
    default: () => <div>股票池页面</div>,
  }))
);
const TradePage = lazy(() =>
  import("./pages/trade/TradePage").catch(() => ({
    default: () => <div>交易页面</div>,
  }))
);

// Placeholder pages for remaining routes
const Placeholder = ({ title }: { title: string }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "60vh",
      color: "#8887a8",
      fontSize: 18,
    }}
  >
    {title} — 开发中
  </div>
);

const AgentDiscussionPage = () => <Placeholder title="碎片聚合" />;
const KlineSignalPage = () => <Placeholder title="K线星象" />;
const BacktestPage = () => <Placeholder title="回测时光" />;
const StrategyPerfPage = () => <Placeholder title="修行日记" />;
const ExperiencePage = () => <Placeholder title="内观" />;
const NotificationPage = () => <Placeholder title="回音" />;
const SystemHealthPage = () => <Placeholder title="系统脉搏" />;
const SettingsPage = () => <Placeholder title="内观设置" />;
const EquityCurvePage = () => <Placeholder title="星轨" />;
const DataMonitorPage = () => <Placeholder title="天眼" />;
const NewsPage = () => <Placeholder title="心念潮汐" />;

function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <ProtectedRoute>
              <PcLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/stock-pool" element={<StockPoolPage />} />
          <Route path="/agent-discussion" element={<AgentDiscussionPage />} />
          <Route path="/trade" element={<TradePage />} />
          <Route path="/kline-signal" element={<KlineSignalPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/strategy-perf" element={<StrategyPerfPage />} />
          <Route path="/experience" element={<ExperiencePage />} />
          <Route path="/notification" element={<NotificationPage />} />
          <Route path="/system-health" element={<SystemHealthPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/equity-curve" element={<EquityCurvePage />} />
          <Route path="/data-monitor" element={<DataMonitorPage />} />
          <Route path="/news" element={<NewsPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
