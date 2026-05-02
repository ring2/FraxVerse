# Frontend Phase 1 — FraxVerse Web UI Implementation Plan

> **核心原则：** 先搭骨架再填肉。Phase 1 完成项目初始化 + 核心基础页面（登录+仪表盘+股票池+交易），确保可运行。

**Goal:** 搭建 FraxVerse 前端项目脚手架，完成4个核心页面的基础版本，对接FastAPI后端API。

**Architecture:** React 18 + TypeScript + Vite + Ant Design 5.x + Zustand + lightweight-charts + Tailwind CSS

**Backend API base:** http://localhost:8000/api/v1

---

### Task 1: 前端项目初始化（Vite + React + TS）

**Objective:** 用 Vite 创建前端项目骨架，安装全部依赖

**Files:**
- Create: `frontend/` 整个项目
- 配置: `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `package.json`

**Step 1:** 创建项目并安装依赖
```bash
cd /home/ubuntu/FraxVerse
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install antd@5 @ant-design/icons zustand axios react-router-dom@6 tailwindcss@3 postcss autoprefixer
npm install lightweight-charts echarts echarts-for-react
npm install @types/react @types/react-dom -D
npx tailwindcss init -p
```

**Step 2:** 配置 Tailwind（tailwind.config.ts - content paths）
**Step 3:** 配置 Vite proxy 代理到 FastAPI（localhost:8000）
**Step 4:** 清理默认文件，准备基础入口

**Verify:** `npm run dev` 可正常启动

---

### Task 2: 品牌主题系统 + 全局样式

**Objective:** 实现 FraxVerse 深空宇宙视觉主题

**Files:**
- Create: `frontend/src/theme/colors.ts`
- Create: `frontend/src/theme/fraxTheme.ts`
- Create: `frontend/src/App.css` (全局深空背景)
- Modify: `frontend/src/index.css`

**Step 1:** 定义色彩系统（深空背景 #0a0a1a、星云紫 #6b5ce7、星芒金 #f0c040、碎片蓝 #4a9eff）
**Step 2:** 配置 Ant Design 5.x 的 ConfigProvider 主题 Token

**Verify:** 浏览器打开后背景为深空色

---

### Task 3: 路由体系 + 布局组件

**Objective:** 实现 PC 端侧边栏布局 + react-router 路由体系

**Files:**
- Create: `frontend/src/components/layout/PcLayout.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/common/ProtectedRoute.tsx`
- Create: `frontend/src/components/common/ErrorBoundary.tsx`
- Create: `frontend/src/components/common/LoadingFallback.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

**Step 1:** 实现 ProtectedRoute（检查 isAuthenticated）
**Step 2:** 实现 PcLayout（左侧侧边栏 + 右侧内容区）
**Step 3:** 配置路由表（12个页面的 lazy load 路由）

**Verify:** 访问 /login → 登录页，访问 /dashboard → 跳回 /login（未登录时）

---

### Task 4: API 服务层 + Zustand 认证状态

**Objective:** axios 实例 + 认证 API 调用 + 认证状态管理

**Files:**
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/authService.ts`
- Create: `frontend/src/stores/useAuthStore.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/types/common.ts`

**Step 1:** 创建 axios 实例（baseURL + 拦截器自动带 Token）
**Step 2:** 实现 authService（login/logout/refresh/checkInit）
**Step 3:** 实现 useAuthStore（Zustand 认证状态）

**Verify:** 单元测试（mock axios 验证 login 流程）

---

### Task 5: 登录页（星门）

**Objective:** 实现美观的深空风格登录页面

**Files:**
- Create: `frontend/src/pages/login/LoginPage.tsx`

**Includes:**
- 深空背景 + 核心粒子背景（简版）
- FraxVerse 品牌Logo
- 用户名/密码输入 + 记住我 + 登录按钮
- Token 存储（localStorage/sessionStorage）
- 错误提示

**Verify:** 输入正确的用户名密码 → 跳转到 /dashboard

---

### Task 6: 仪表盘（宇宙总览）

**Objective:** 系统总览看板

**Files:**
- Create: `frontend/src/pages/dashboard/DashboardPage.tsx`
- Create: `frontend/src/stores/useMarketStore.ts`
- Create: `frontend/src/services/marketService.ts`

**Includes:**
- 市场状态卡片（当前状态、仓位建议）
- 账户概览（总资产、持仓市值、可用资金、今日盈亏）
- 股票池概览（候选数量、评分范围）
- 最近风控事件列表

**Verify:** 页面渲染正常，Mock数据可见

---

### Task 7: 股票池页（碎片候选）

**Objective:** 策略筛选结果的可视化

**Files:**
- Create: `frontend/src/pages/stock-pool/StockPoolPage.tsx`
- Create: `frontend/src/stores/useStrategyStore.ts`
- Create: `frontend/src/services/strategyService.ts`

**Includes:**
- 策略筛选结果列表（Table）
- 评分展示（五维度雷达图）
- 筛选条件卡片

**Verify:** 页面渲染正常

---

### Task 8: 交易页（交易星图）

**Objective:** 持仓管理 + 下单

**Files:**
- Create: `frontend/src/pages/trade/TradePage.tsx`
- Create: `frontend/src/stores/useTradeStore.ts`
- Create: `frontend/src/services/tradeService.ts`

**Includes:**
- 当前持仓列表
- SIMULATION 模式下单调单
- 止损设置

**Verify:** 页面渲染正常

---

### Task 9: 全量回归测试 + Git 提交

**Objective:** 确保前端构建正常，代码质量通过

**Files:**
- npm run build 无错误
- ESLint 检查通过

**Verify:** `npm run build` 成功
