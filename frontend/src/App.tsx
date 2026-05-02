import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import PcLayout from "./components/layout/PcLayout";
import MobileLayout from "./components/layout/MobileLayout";
import ProtectedRoute from "./components/common/ProtectedRoute";
import LoadingFallback from "./components/common/LoadingFallback";

// Lazy load PC pages
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

const AgentDiscussionPage = lazy(() =>
  import("./pages/agent-discussion/AgentDiscussionPage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        碎片聚合
      </div>
    ),
  }))
);

const StrategyPerfPage = lazy(() =>
  import("./pages/strategy-perf/StrategyPerfPage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        修行日记
      </div>
    ),
  }))
);

const ExperiencePage = lazy(() =>
  import("./pages/experience/ExperiencePage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        内观
      </div>
    ),
  }))
);

const NotificationPage = lazy(() =>
  import("./pages/notification/NotificationPage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        回音
      </div>
    ),
  }))
);

const SystemHealthPage = lazy(() =>
  import("./pages/system-health/SystemHealthPage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        系统脉搏
      </div>
    ),
  }))
);

const EquityCurvePage = lazy(() =>
  import("./pages/equity-curve/EquityCurvePage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        星轨
      </div>
    ),
  }))
);

const DataMonitorPage = lazy(() =>
  import("./pages/data-monitor/DataMonitorPage").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        天眼
      </div>
    ),
  }))
);

// Lazy load mobile pages
const MobileDashboard = lazy(() =>
  import("./pages/mobile/MobileDashboard").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        看盘
      </div>
    ),
  }))
);
const MobileStockPool = lazy(() =>
  import("./pages/mobile/MobileStockPool").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        股票池
      </div>
    ),
  }))
);
const MobileTrade = lazy(() =>
  import("./pages/mobile/MobileTrade").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        交易
      </div>
    ),
  }))
);
const MobileSettings = lazy(() =>
  import("./pages/mobile/MobileSettings").catch(() => ({
    default: () => (
      <div style={{ padding: 40, color: "#8887a8", textAlign: "center" }}>
        设置
      </div>
    ),
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

const KlineSignalPage = () => <Placeholder title="K线星象" />;
const BacktestPage = () => <Placeholder title="回测时光" />;
const SettingsPage = () => <Placeholder title="内观设置" />;
const NewsPage = () => <Placeholder title="心念潮汐" />;

// Device-aware root redirect sends to login (device detection happens on login)
const RootRedirect = () => {
  return <Navigate to="/login" replace />;
};

// Catch-all
const CatchAllRedirect = () => {
  return <Navigate to="/login" replace />;
};

function AppContent() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Login is shared across devices */}
        <Route path="/login" element={<LoginPage />} />

        {/* PC routes */}
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
        </Route>

        {/* Mobile routes */}
        <Route
          element={
            <ProtectedRoute>
              <MobileLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/m/dashboard" element={<MobileDashboard />} />
          <Route path="/m/stock-pool" element={<MobileStockPool />} />
          <Route path="/m/trade" element={<MobileTrade />} />
          <Route path="/m/settings" element={<MobileSettings />} />
        </Route>

        {/* Device-aware redirects */}
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<CatchAllRedirect />} />
      </Routes>
    </Suspense>
  );
}

function App() {
  return <AppContent />;
}

export default App;
