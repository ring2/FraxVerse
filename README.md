# 碎片宇宙（FraxVerse）智能量化交易系统

> **万千心念皆碎片，一怀内观即宇宙**
> *Every thought is a fragment; inner vision is the universe.*

基于**经验驱动型量化**方法论的 A 股全自动智能量化交易系统。不是靠玄学预测涨跌，而是**把每次操作沉淀为结构化经验，在下一次场景匹配时辅助决策**——交易即修行，复利靠迭代。

---

## 核心理念

| 原则 | 说明 |
|------|------|
| **交易修心** | 每一笔交易都是心念的投射，系统仅是修行的工具 |
| **经验驱动** | 行情会变，人性不变。结构化经验是系统的核心资产 |
| **复利迭代** | 追求稳定盈利、少回撤、小盈利，靠复利活下来 |
| **AI 增强** | 四位 AI-Agent 模拟团队讨论制，多视角交叉验证 |
| **质量优先** | 每完成一个功能必须验证 + 测试 + git push，不欠技术债 |

### 两套核心策略

1. **周期底部量能异动** — 识别底部放量、主力吸筹信号
2. **趋势动量低吸** — 捕捉上升趋势中的回调低吸机会

---

## 功能概述

### 当前阶段（P0 — 最小可验证产品）

| 模块 | 状态 | 说明 |
|------|------|------|
| 🔐 **认证系统** | ✅ | JWT 双 Token（Access + Refresh）+ bcrypt 密码 + 登录锁 |
| 📊 **看盘 Dashboard** | ✅ | 总资产/盈亏/信号/经验四维指标 + AI 讨论摘要 |
| 📋 **股票池** | ✅ | 五维度评分排序（量价/资金/情绪/主力/逻辑） |
| 🛒 **交易执行** | ✅ | 模拟/实盘双模式，下单与持仓管理 |
| 🧠 **AI-Agent 讨论** | ✅ | 四位 Agent 多轮讨论 + 加权投票 + LLM 预算管理 |
| 📓 **经验库** | ✅ | 操作归档 → 结构化经验 → 场景匹配辅助决策 |
| 📈 **权益曲线** | ✅ | 账户净值追踪与可视化 |
| 🔔 **通知系统** | ✅ | 微信推送 + 系统内通知 |
| 🩺 **系统健康** | ✅ | 数据源/Agent/风险监控状态 |
| 👁 **数据监控（天眼）** | ✅ | 市场全景 + 板块轮动监控 |

### 规划中（P1+）

- K线星象（技术分析可视化）
- 回测时光（回测引擎集成）
- 心念潮汐（新闻情绪流）
- 内观设置（系统配置中心）

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 (React + Vite)                  │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │  PC 端   │ │   移动端   │ │ LoginPage│ │  共享组件  │  │
│  │ Dashboard│ │ MobileLayout│ │ 粒子动画  │ │ SectionCard│ │
│  │  等16页  │ │  Tab导航   │ │ +涟漪特效 │ │ MetricCard│ │
│  └─────────┘ └──────────┘ └──────────┘ └─────────┘  │
│              ThemeContext (Light/Dark 双主题)         │
│       毛玻璃UI + 入场动画 + 紫色渐变设计语言            │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/REST (JWT Auth)
┌───────────────────────▼─────────────────────────────┐
│               后端 API (FastAPI)                       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────────┐  │
│  │ Auth │ │Trade │ │Market│ │Agent │ │ Misc(监控/  │  │
│  │ 认证  │ │ 交易  │ │ 行情  │ │ AI讨论│ │ 经验/通知) │  │
│  └──────┘ └──────┘ └──────┘ └──────┘ └───────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│               AI-Agent 决策引擎                        │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Hunter  │ │Detective │ │ Catcher │ │  Judge   │  │
│  │ 主线猎手  │ │ 资金侦探   │ │ 情绪捕手  │ │ 经验法官   │  │
│  └─────────┘ └──────────┘ └─────────┘ └──────────┘  │
│    ┌──────────────┐  ┌──────────────┐                │
│    │ 加权投票系统   │  │ 校准/退化引擎  │                │
│    │  + LLM预算管理 │  │ (Token不足时) │                │
│    └──────────────┘  └──────────────┘                │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│          数据层 (PostgreSQL + Redis)                  │
│  用户/会话 │ 股票池 │ 交易记录 │ 经验库 │ Agent讨论记录  │
│  权益曲线 │ 通知 │ 系统配置 │ 数据质量 │ 风控日志       │
└─────────────────────────────────────────────────────┘
```

### 前端架构

```
React 18 + TypeScript + Vite + Ant Design 5.x
├── 双主题体系 (Light/Dark Token → ConfigProvider 联动)
├── 毛玻璃 UI 设计语言（backdrop-filter blur + 紫色渐变）
├── 移动端优先响应式（MobileLayout + Tab 导航）
├── Zustand 状态管理（useAuthStore）
└── 共享组件库：SectionCard / MetricCard / AgentBubble / Tag / Button / EmptyState
```

### 后端架构

```
FastAPI + Python 3.11 + SQLAlchemy 2.0 (async)
├── JWT 双 Token 认证（Access 30min + Refresh 7天）
├── 10 个 API 路由模块（auth / trade / market / agent / strategy / risk / experience / monitor / notification / misc）
├── AI-Agent 决策引擎（4 Agent 讨论 → 加权投票 → 校准 → 降级）
├── 五维度评分系统（量价 / 资金 / 情绪 / 主力 / 逻辑）
└── 数据采集模块（AKShare 新浪接口 + 板块数据 + 资金流）
```

### AI-Agent 系统

四位虚拟交易员组成"团队讨论制"决策机制：

| Agent | 角色 | 职责 |
|-------|------|------|
| 🎯 **Hunter 主线猎手** | 市场雷达 | 追踪主线板块、龙头股识别、趋势强度判断 |
| 🔍 **Detective 资金侦探** | 资金分析 | 北向资金、主力净流入、大单占比、筹码分析 |
| 🌊 **Catcher 情绪捕手** | 情绪感知 | 新闻情绪、板块热度、市场恐慌/贪婪指数 |
| ⚖️ **Judge 经验法官** | 经验匹配 | 历史上相似场景回顾、交易案例匹配、结果复盘 |

工作流程：**权重校准 → 预算检查 → 风控前置 → 并发讨论 → 多轮辩论 → 加权投票 → 决策输出**

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite 8 | SPA 应用框架 |
| | Ant Design 5.x | UI 组件库 |
| | Zustand | 状态管理 |
| | React Router v7 | 路由管理 |
| | Vitest | 单元测试 |
| **后端** | FastAPI + Python 3.11 | REST API |
| | SQLAlchemy 2.0 (async) | ORM |
| | Pydantic v2 | 数据校验 |
| | bcrypt + PyJWT | 认证安全 |
| **数据库** | PostgreSQL 16 | 关系数据库 |
| | Redis 7 | 缓存/队列 |
| **AI** | DeepSeek API | Agent LLM 调用 |
| **数据** | AKShare (新浪接口) | A股行情数据 |
| **部署** | Docker + Docker Compose | 容器化 |
| | Uvicorn + Nginx | 生产部署 |

---

## 部署启动

### 环境要求

- Node.js ≥ 18
- Python ≥ 3.11
- PostgreSQL 16 + Redis 7（或 Docker）

### 快速启动（开发环境）

```bash
# 1. 克隆仓库
git clone https://github.com/ring2/FraxVerse.git
cd FraxVerse

# 2. 启动数据库
docker compose up -d    # PostgreSQL + Redis

# 3. 初始化数据库
psql -h localhost -U fraxverse -d fraxverse -f src/db/schema.sql
psql -h localhost -U fraxverse -d fraxverse -f src/db/seed.sql

# 4. 后端
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 前端
cd frontend
npm install
npm run dev              # → http://localhost:3000
```

### 生产部署

```bash
# 构建前端
cd frontend && npm run build    # → dist/

# 后端生产启动
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 或使用 Docker Compose
docker compose -f docker-compose.prod.yml up -d
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串（异步） | `postgresql+asyncpg://fraxverse:***@localhost:5432/fraxverse` |
| `SYNC_DATABASE_URL` | PostgreSQL 连接串（同步） | `postgresql://fraxverse:***@localhost:5432/fraxverse` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | **(必填)** |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | **(Agent功能必填)** |
| `DEBUG` | 调试模式 | `false` |

### 验证健康状态

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","db":"connected","redis":"connected"}
```

---

## 项目结构

```
FraxVerse/
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── components/          # 共享组件
│   │   │   ├── layout/          # PcLayout, MobileLayout, Sidebar, Header
│   │   │   ├── mobile/          # SectionCard, MetricCard, AgentBubble, Button...
│   │   │   └── common/          # ProtectedRoute, EmptyState, LoadingFallback
│   │   ├── pages/               # 页面
│   │   │   ├── login/           # 登录页（粒子动画+毛玻璃）
│   │   │   ├── mobile/          # 移动端10个页面
│   │   │   └── dashboard/...    # PC端页面
│   │   ├── theme/               # 双主题系统（Light/Dark Tokens）
│   │   ├── services/            # API 调用层
│   │   ├── stores/              # Zustand 状态管理
│   │   └── hooks/               # 自定义 Hooks
│   └── package.json
├── src/                         # Python 后端
│   ├── api/                     # FastAPI 路由
│   │   ├── main.py              # 应用入口
│   │   └── routes/              # auth, trade, market, agent, misc...
│   ├── agent/                   # AI-Agent 决策引擎
│   │   ├── orchestrator.py      # 主调度器
│   │   ├── models.py            # Pydantic结构化输出
│   │   ├── llm_client.py        # LLM 调用封装
│   │   ├── voting.py            # 加权投票
│   │   ├── calibration.py       # 权重校准
│   │   ├── degradation.py       # 降级策略
│   │   └── budget.py            # LLM预算管理
│   ├── strategy/                # 策略引擎
│   │   ├── screener.py          # 粗筛
│   │   ├── scorer.py            # 五维度评分
│   │   ├── state_machine.py     # 状态机
│   │   └── backtest_runner.py   # 回测引擎
│   ├── data/                    # 数据采集
│   ├── db/                      # 数据库模型
│   ├── schemas/                 # Pydantic Schema
│   └── config.py                # 配置
├── docker-compose.yml           # 开发环境
├── requirements.txt
└── README.md
```

---

## 开发规范

### 代码质量

```bash
# 运行全部测试
cd frontend && npm test           # 前端测试
pytest tests/ -v                  # 后端测试

# 代码检查
ruff check .                      # Python 代码检查
cd frontend && npx tsc --noEmit   # TypeScript 类型检查
cd frontend && npm run lint       # ESLint

# 构建验证
cd frontend && npm run build      # 前端构建（含类型检查）
```

### 开发流程

每完成一个功能点：**代码实现 → 测试 → lint → git commit → git push → 微信推送进度**

---

## 设计语言

FraxVerse 的 UI 设计语言围绕"碎片宇宙"的哲学意象展开：

- **🟣 主色调** — 紫色渐变 (`#7F77DD` → `#5F56C8`)，象征心念与宇宙的连接
- **🪟 毛玻璃质感** — `backdrop-filter: blur(12-24px)` + 半透明背景
- **✨ 微动效** — 页面入场淡入、卡片悬浮提升、粒子星尘背景、点击涟漪
- **🌓 双主题** — Light/Dark 模式一键切换，所有组件响应
- **📱 移动优先** — 底部 Tab 导航 + 手势友好的交互区域

---

## 许可

MIT License © 2025 碎片宇宙（FraxVerse）
