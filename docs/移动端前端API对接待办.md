# 移动端前端 — 未对接真实后端 API 的待办清单

> **生成时间：** 2026-05-03
> **来源：** 逐页扫描所有移动端页面 + service 层 + 后端路由
> **结论：** 所有 9 个移动端页面的 service 层已**全部写了真实 API 调用**（前端→后端），
> 后端路由也**全部实现了**。剩余问题集中在：
> 1. 前端某些交互按钮仍停留在 `message.info('开发中')` 占位
> 2. 部分数据源（信号列表、AI 讨论摘要）用硬编码 mock 而非从后端获取

---

## 一、概览

| 页面 | Service API | 已对接 | 待对接交互 | Mock 数据问题 |
|:----|:-----------|:-----:|:---------|:------------|
| MobileDashboard 看盘 | portfolio/trade/market | ✅ 全部 | 3 处 | ⚠️ 信号/AI讨论 mock |
| MobileStockPool 股票池 | strategy/trade | ✅ 全部 | 2 处 | ⚠️ metrics/涨幅 mock |
| MobileTrade 交易 | trade | ✅ 全部 | 4 处 | 无 |
| MobileAi AI 分析 | agent | ✅ 全部 | 少量 | 无 |
| MobileExperience 经验 | experience | ✅ 全部 | 无 | 无 |
| MobileEquity 权益曲线 | (仅图表) | N/A | 无 | 无 |
| MobileMonitor 监控 | monitor | ✅ 全部 | 无 | 有 mock fallback |
| MobileNotifications 通知 | notification | ✅ 全部 | 无 | 有 mock fallback |
| MobileSettings 设置 | (无 API) | N/A | 无 | 无 |
| MobileSystemHealth 系统健康 | monitor | ✅ 全部 | 无 | 有 mock fallback |
| MobileMore 更多 | (仅导航) | N/A | 无 | 无 |

---

## 二、具体待办项

### 2.1 前端交互按钮「开发中」— 3 个页面 9 处

#### MobileDashboard.tsx（3 处）

| 行号 | 按钮 | 现状 | 需要对接的 API |
|:---:|:----|:----|:-------------|
| 106 | 信号卡片点击 | `message.info("查看详情 — 开发中")` | 需跳转到标的详情页或弹窗展示 |
| 131 | 查看全部信号 | `message.info("查看全部信号 — 开发中")` | 需跳转到 MobileStockPool 页 |
| 135 | AI 分析详情 | `message.info("AI 分析详情 — 开发中")` | 需跳转到 MobileAi 页或展示弹窗 |

#### MobileStockPool.tsx（2 处）

| 行号 | 按钮 | 现状 | 需要对接的 API |
|:---:|:----|:----|:-------------|
| 116 | 重新扫描 | `message.info("重新扫描 — 开发中")` | `POST /api/v1/agent/trigger` 已实现 |
| 121 | 查看详情 | `message.info("查看 ${code} 详情 — 开发中")` | 需跳转到行情详情/K线页（后端 getKlines 已实现） |

#### MobileTrade.tsx（4 处）

| 行号 | 按钮 | 现状 | 需要对接的 API |
|:---:|:----|:----|:-------------|
| ? | 市价买入 | `message.info("市价买入 — 开发中")` | `POST /api/v1/trade/orders` 已实现 |
| ? | 限价买入 | `message.info("限价买入 — 开发中")` | 同上 |
| ? | 撤单 | `message.info("撤单 — 开发中")` | `POST /api/v1/trade/orders/{id}/cancel` 已实现 |
| ? | 一键调仓 | `message.info("一键调仓 — 开发中")` | 需组合下单 API |
| ? | 快速平仓 | `message.info("快速平仓 — 开发中")` | 需遍历持仓逐个下单 |

---

### 2.2 Mock 数据替换 — 2 个页面 3 处

#### MobileDashboard.tsx — 信号列表硬编码

- **文件：** `frontend/src/pages/mobile/MobileDashboard.tsx` 第 27-55 行
- **问题：** `MOCK_SIGNALS` 硬编码 3 只 mock 标的（茅台、宁德、五粮液），
  前端没有调用后端获取实时信号/决策列表
- **解决：** 在 Dashboard 的 `useEffect` 里增加 `agentService.getDecisions({ pageSize: 3 })` 调用，
  用返回的当日决策替代 `MOCK_SIGNALS`
- **后端：** `GET /api/v1/agent/decisions` 已实现

#### MobileDashboard.tsx — AI 讨论硬编码

- **文件：** 同上第 57-61 行
- **问题：** `MOCK_AGENT_DISCUSSIONS` 硬编码 3 条 mock agent 讨论
- **解决：** 用 `agentService.getDiscussions({ pageSize: 3 })` 替代
- **后端：** `GET /api/v1/agent/discussions` 已实现

#### MobileStockPool.tsx — 评分指标硬编码

- **文件：** `frontend/src/pages/mobile/MobileStockPool.tsx` 第 75-95 行
- **问题：** `data.map()` 中 metrics（量价/资金/情绪/主力）全部硬编码为 80，
  change 字段用假数据 `"final_decision === 'buy' ? '+0.0%' : '-0.0%'"`
- **解决：** 目前后端的 StockPool 表没有这些细分指标字段，
  需要加字段或前端先保留 mock

---

## 三、优先级建议

### 🔴 高优先级（影响核心使用体验）

1. **MobileTrade.tsx — 下单/撤单按钮接通**（4 处）
   - 后端 API 已全实现，只是前端按钮没连
   - 打通后就能在移动端手动操作了

2. **MobileDashboard.tsx — 信号列表接通后端**（2 处）
   - 后端 `GET /agent/decisions` 已实现
   - 替代硬编码 mock，显示真实信号

### 🟡 中优先级（补充体验）

3. **MobileStockPool.tsx — 重新扫描按钮**（1 处）
   - 后端 `POST /agent/trigger` 已实现
   - 接通后可在移动端触发扫描

4. **MobileStockPool.tsx — 查看详情跳转**（1 处）
   - 跳转到一个标的详情页（需新建或复用已有页面）

### 🟢 低优先级（锦上添花）

5. **MobileStockPool.tsx — metrics 指标数据**（后端无此字段）
   - 需要加后端字段或后续补充

---

## 四、文件索引

| 文件 | 行数 | 类型 |
|:----|:---:|:----|
| `frontend/src/pages/mobile/MobileDashboard.tsx` | 432 | 页面 |
| `frontend/src/pages/mobile/MobileStockPool.tsx` | 471 | 页面 |
| `frontend/src/pages/mobile/MobileTrade.tsx` | ~500 | 页面 |
| `frontend/src/services/portfolioService.ts` | ~30 | Service |
| `frontend/src/services/tradeService.ts` | ~75 | Service |
| `frontend/src/services/agentService.ts` | ~200 | Service |
| `frontend/src/services/strategyService.ts` | ~55 | Service |
| `backend/src/api/routes/trade.py` | ~150 | 后端路由 |
| `backend/src/api/routes/agent.py` | ~350 | 后端路由 |
| `backend/src/api/routes/misc.py` | 170 | 后端路由 |
