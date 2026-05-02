# FraxVerse Agent 上下文手册

> 本文件是 Hermes Agent 的核心上下文来源。Memory 清空后，每次会话从此文档加载关键信息。
> 最后更新：2026-05-02

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

---

## 二、项目状态

### ✅ 已完成

| 阶段 | 完成度 | 说明 |
|:----|:-----:|:-----|
| P0 纯规则引擎 | 100% | 采集→筛选→评分→信号，全链路跑通 |
| P1 前后端基础设施 | ~95% | React+FastAPI+PostgreSQL+Redis |
| P2 AI Agent | 100% | 4 角色辩论→投票→校准→降级，Mock LLM 模式通过 |
| 安全审计修复 | 100% | JWT认证、SQL注入、吞异常修复 |
| V2 移动端 | ~100% | 4主页面+6子页面+登录页+双主题+底部Tab导航 |
| P0遗留（L1-L5） | 100% | 空状态提示(EmptyState组件)、404页面(NotFoundPage+路由兜底)、Loading统一(Suspense+LoadingFallback)、错误提示(App.useApp+toast)、移动端适配(100dvh+自适应) |
| DeepSeek API Key | ✅ 已配 | `.env`→`DEEPSEEK_API_KEY=***`，真实API测试3/3通过（deepseek-v4-flash 1.1~4s延迟） |

### 🚨 已知问题

| 等级 | 问题 | 状态 |
|:---:|:----|:----:|
| P0 | stock_code 格式兼容（前端输入 600519 自动补全 → 600519.SH） | ✅ 已修 |
| P0 | 6个子页面骨架→真实内容 | ✅ 已修 |
| P1 | authService.changePassword 封装 | ✅ 已修 |
| P1 | misc.py 废弃 agent_router（40行冗余） | ✅ 已修 |
| P1 | 5个前端pc页面mock→API（ROADMAP遗留项） | ⬜ 待确认 |
| - | 后端测试 `ModuleNotFoundError: jose`（python-jose 未安装） | ❌ 未修 |
| - | 前端测试 4 failed / 28（2 test files fail） | ❌ 未修 |
| - | 后端服务未运行（uvicorn 未启动） | ❌ 未修 |

### ⬜ 待办清单

> ✅ 标记 = 已确认完成，待 ROADMAP.md 同步更新

#### ✅ P0 遗留 — 基础体验（已完成）

- [x] **L1 — 空状态提示**：全局 EmptyState + MobileEmptyState 组件
- [x] **L2 — 前端 404 页面**：NotFoundPage + Route path="*" 兜底
- [x] **L3 — Loading 状态统一**：LoadingFallback + Suspense
- [x] **L4 — 错误提示统一**：App.useApp toast
- [x] **L5 — 移动端适配收尾**：100dvh、自适应

#### ✅ P3 — 真数据（API Key 已配）

- [x] **P3-1 — 配置 DEEPSEEK_API_KEY**：`.env` 已配，3 个真实 API 测试通过
- [ ] **P3-2 — 完整回测跑一轮**：backtesting 库跑 2 年历史数据 + 报告
- [ ] **P3-3 — 实盘/模拟盘持续运行**：配置 cron 每日自动触发

#### DevOps

- [ ] **D1 — Alembic 初始化**：自动生成初始迁移
- [ ] **D2 — Docker Compose 完善**：加入前后端容器
- [ ] **D3 — GitHub CI**：自动测试 + 构建
- [ ] **D4 — README 完善**

---

## 三、品牌设计规范

### 颜色系统

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `brand` | `#7F77DD` | `#6C5CE7` | 品牌紫色 |
| `semantic.up`（涨） | `#E8735A` 珊瑚红 | `#F0856E` | 上涨/正值 |
| `semantic.down`（跌） | `#4DB899` 翡翠绿 | `#5CC4A6` | 下跌/负值 |
| `bg.page` | `#FAF9F7` | 深色 | 页面背景 |
| `bg.surface` | `#FFFFFF` | 深色 | 卡片/表面 |

> 涨跌色是 A 股惯例的反向：涨=红/珊瑚色，跌=绿/翡翠色

### 前端主题系统

- Light/Dark 双主题，256 组 Token（`FraxThemeColors` 类型）
- `useTheme()` hook 提供当前 `{ colors, isDark, theme }`
- 前端入口：`App.tsx` 中 `ConfigProvider` + `ThemeContext`
- `MobileSectionCard` 组件：卡片容器（带 title + 双主题适配）

### AntD 已知坑

- **antd v5 + React 19**：`message` 等静态 API 静默失败，必须用 `App.useApp()` 替代
- **antd v5.22+**：`bodyStyle` 已废弃，需用 `styles.body`
- **100vh bug（iOS Safari）**：地址栏动态伸缩导致视口高度不一致，`height: 100vh` → `100dvh`

---

## 四、架构关键

### 前后端 API 对齐方案

```
后端 Pydantic schema（唯一真实来源）
        ↓ /openapi.json
openapi-typescript 自动生成
        ↓
api-generated.ts（68849 字节，自动生成，不手动编辑）
        ↓ + 补充
api-extended.ts（前端独有类型）
```

- `npm run gen:api`：拉取最新 schema 生成
- `npm run ci`：`gen:api → tsc → vitest → vite build`

### 开发流程规范

1. 每完成一个功能 → **功能验证 + 自动化测试**
2. 测试通过 → **git commit + push**
3. Push 成功 → **微信推送进度总结**
4. **前端 build 前排除测试文件**：`tsconfig.build.json` 继承 `tsconfig.app.json` 但 `exclude` 掉 `src/**/*.test.*`
5. 每次修复后必须**真实重测全链路**，不能只看代码修改

### 构建验证

```bash
# 前端
npx tsc --noEmit --project tsconfig.build.json  # 零错误
npx vite build                                    # 零错误

# 后端
python -m pytest tests/ -x -q --tb=short          # 全绿
```

---

## 五、重要经验库

### Docker
- PostgreSQL + Redis 容器运行中：`fraxverse-db`, `fraxverse-redis`
- 后端 uvicorn + 前端 dev server 需手动启动

### Git
- `git remote set-url origin https://github.com/ring2/FraxVerse.git`
- credential 已配置 store 模式（`~/.git-credentials`）
- 直接 `git push` 即可推送（前提网络通）

### 编辑器/环境
- 工作目录：`/home/ubuntu/FraxVerse/`
- Backend：FastAPI at `/home/ubuntu/FraxVerse/src/api/main.py`
- Frontend：Vite+React at `/home/ubuntu/FraxVerse/frontend/`
- Python venv：`.venv/`（uv 管理）
- PostgreSQL + Redis：Docker 容器运行中

---

## 六、关键文件索引

| 文件 | 说明 |
|------|------|
| `docs/ROADMAP.md` | 进化路线图（优先做此文件的待办） |
| `docs/需求分析/00-综合PRD文档.md` | 综合PRD |
| `docs/需求分析/01-系统技术架构设计.md` | 技术架构设计 |
| `docs/需求分析/02-开发质量保障与提交规范.md` | 质量保障规范 |
| `docs/详细设计/DD-01~09` | 9个模块详细设计 |
| `docs/设计稿/FraxVerse-品牌视觉设计规范.md` | 品牌视觉规范 |
| `docs/AGENT-CONTEXT.md` | **本文档 — Agent 上下文手册** |

### 前端页面

| 页面 | 路径 | 状态 |
|:----|:-----|:----:|
| MobileDashboard | `frontend/src/pages/mobile/MobileDashboard.tsx` | ✅ |
| MobileStockPool | `frontend/src/pages/mobile/MobileStockPool.tsx` | ✅ |
| MobileTrade | `frontend/src/pages/mobile/MobileTrade.tsx` | ✅ |
| MobileSettings | `frontend/src/pages/mobile/MobileSettings.tsx` | ✅ |
| MobileAi | `frontend/src/pages/mobile/MobileAi.tsx` | ✅ |
| MobileExperience | `frontend/src/pages/mobile/MobileExperience.tsx` | ✅ |
| MobileNotifications | `frontend/src/pages/mobile/MobileNotifications.tsx` | ✅ |
| MobileEquity | `frontend/src/pages/mobile/MobileEquity.tsx` | ✅ |
| MobileMonitor | `frontend/src/pages/mobile/MobileMonitor.tsx` | ✅ |
| MobileSystemHealth | `frontend/src/pages/mobile/MobileSystemHealth.tsx` | ✅ |
| LoginPage | `frontend/src/pages/login/LoginPage.tsx` | ✅ |

---

## 七、当前 session 的即时任务状态

> 此区域由 Hermes Agent 在每个会话中维护，记录当前正在做的工作

**当前分支：** `main`
**最新 commit：** `6e4efa4` — fix: 前端子页面 colors 作用域修复
**未 push 变更：** 无（已同步）
**后端服务：** 停止中
**前端 dev server：** 停止中
**已知阻碍：**
- 后端测试因缺少 `python-jose` 模块而失败
- 前端测试 2 files failed（LoginPage 渲染）
- CN 网络到 GitHub 不稳定（上次推成功但超~30s）

---

### 附录：Memory 清理记录

> 原 Memory（10条 / 2085字符）于 2026-05-02 清空，内容归纳至本文档。
> 此后 Memory 仅保存核心指针：`AGENT-CONTEXT.md 是最新上下文来源，非特殊情况勿覆盖此指针。`
