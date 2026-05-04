# FraxVerse Agent 上下文手册

> 本文件是 Hermes Agent 的核心上下文来源。Memory 清空后，每次会话从此文档加载关键信息。
> 最后更新：2026-05-04

---

## 一、项目概况

| 项目 | 值 |
|------|-----|
| 项目名 | 碎片宇宙（FraxVerse）智能量化交易系统 |
| 品牌哲学 | 交易修心、心念为碎片、宇宙为心之投影 |
| 技术栈 | React 19 + AntD v5 + FastAPI + PostgreSQL + Redis + Docker |
| 创始人 | INTJ+处女座，6年A股交易经验个人投资者 |
| 核心理念 | 经验驱动型量化——每次操作归档为结构化经验，场景匹配辅助决策 |
| 核心策略 | 周期底部量能异动 + 趋势动量低吸 |
| 文档位置 | `/home/ubuntu/FraxVerse/docs/` |
| Git 仓库 | `https://github.com/ring2/FraxVerse.git`（credential store 已配） |
| 当前分支 | `main`（最新 commit `b82248a`） |
| 工作目录 | `/home/ubuntu/FraxVerse/` |

---

## 二、项目状态

### ✅ 已完成

| 阶段 | 完成度 | 说明 |
|:----|:-----:|:-----|
| P0 纯规则引擎 | 100% | 采集→筛选→评分→信号→回测全链路 |
| P1 前后端基础设施 | ~90% | React+FastAPI+PostgreSQL+Redis+Docker 全栈 |
| P2 AI Agent | 100% | 4 角色辩论→投票→校准→降级 |
| DevOps | 90% | Docker Compose ✅ / Alembic ✅ / Mock 清除 ✅ / QueuePool 修复 ✅ |
| 移动端 | 100% | 11 页面 + Mock 清除 + 空数据静默处理 |

### 🔴 P0 进行中

| 项目 | 优先级 | 文档 |
|:-----|:------|:-----|
| P0-1 事件驱动重构（Pipeline→Redis Pub/Sub） | P0 | `docs/P0-1-事件驱动重构-实施计划.md` |

### 🚨 已知问题

| 等级 | 问题 | 状态 |
|:---:|:----|:----:|
| 🔴 | iLink 微信推送 ret=-2（4/30 起，只能收不能发） | 服务端限制，非代码可修 |
| 🟢 | 设计审计测试 4 FAIL（预期 35 表 vs 实际 27 表） | 审计未跟进 Alembic 迁移 |
| 🟢 | FastAPIDeprecationWarning（`regex`→`pattern`） | 兼容性，不影响运行 |
| 🟡 | 磁盘 42G/59G（74%） | 需留意 |

### ⬜ 待办

| 项目 | 优先级 | 估算 |
|:-----|:------|:----:|
| 租 Win 云服务器 + quant-qmt-proxy | P1 | 1h |
| GitHub CI | P2 | 20min |
| 完整回测跑一轮 | P2 | 1h |
| README 完善 | P3 | 1h |

---

## 三、架构关键

### Docker 全栈（所有容器正在运行）

```
postgres:16-alpine  → localhost:5432  (healthy)
redis:7-alpine      → localhost:6379  (healthy)
fraxverse-backend   → :8000           (healthy, 39 endpoints)
fraxverse-frontend  → :3000 → 80      (healthy, Nginx)
```

外网访问：`http://124.220.20.193:3000/`

### 前后端 API 对齐

```
后端 Pydantic schema（唯一真实来源）
        ↓ /openapi.json
openapi-typescript 自动生成
        ↓
api-generated.ts → api-extended.ts
```

### 构建验证

```bash
# 前端
cd frontend && npm run build   # tsc + vite build，零新增错误

# 后端
python -m pytest tests/ -q --tb=short  # 573 passed, 2 skipped
# 需 .venv 环境（uv 管理），或用 Docker 内 Python
```

### 测试说明

- 后端测试需 `.venv` 依赖，当前用 `uv venv .venv && source .venv/bin/activate` 运行
- 5 个失败测试均为设计审计（预期 35 表 vs Alembic 迁移后 27 表），不影响业务功能
- 前端测试需 `cd frontend && npm test`（17 auth + 11 service）

### 已知坑

- **antd v5 + React 19**：`message` 等静态 API 静默失败，必须用 `App.useApp()`
- **antd v5.22+**：`bodyStyle` → `styles.body`
- **100vh（iOS Safari）**：用 `100dvh`
- **Docker 镜像 3.6GB**（backend）：原因是 Python 镜像未精简 + 依赖多，可后续优化

---

## 四、关键文件索引

| 文件 | 说明 |
|------|------|
| `docs/统一待办清单.md` | **当前待办（合并版，最实时）** |
| `docs/开发实施计划.md` | 全阶段开发进度 |
| `docs/AGENT-CONTEXT.md` | **本文档** |
| `src/api/main.py` | FastAPI 主入口 |
| `frontend/src/` | 前端代码 |
| `tests/` | 后端测试（573 passed） |
| `scripts/hermes_cron_push.py` | 微信推送 cron 调度脚本 |
| `/home/ubuntu/hermes_weixin_push.py` | 独立 iLink 推送脚本 |

## 五、重要经验

### Docker 热更新（不改镜像）
```bash
docker cp host/path/file container:/app/path/file
docker compose restart backend
```

### pyproject.toml 快速跑测试
```bash
source .venv/bin/activate  # uv 环境
python -m pytest tests/ -q --tb=short
```

### 前端 mock 清除已完成
MobileTrade/Dashboard/StockPool 三页 MOCK_* 已删除，空数据展示 0 或空列表。
