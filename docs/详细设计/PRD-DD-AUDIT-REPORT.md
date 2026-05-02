# PRD→DD 合规审计报告

> **审计日期**: 2026-05-01
> **审计范围**: PRD(00-综合PRD文档 V1.2) → DD-00/DD-01/DD-02(V1.1)/DD-03
> **审计方法**: 全文扫描PRD强约束(172项)+软约束(33项)，逐条与现有DD文档交叉核对

---

## 一、审计结论

| 等级 | 数量 | 说明 |
|------|------|------|
| **P0 严重偏差** | 3项 | PRD强约束被违反，直接影响实现正确性 |
| **P1 中等偏差** | 5项 | 设计缺失或跨模块不一致，影响开发衔接 |
| **P2 改进建议** | 5项 | 可提升文档质量的优化项 |
| **已修复** | 1项 | DD-02新闻采集(V1.1已修复) |

**核心问题**: 现有DD文档缺乏**需求追溯机制**——没有任何DD文档标注"此设计源自PRD第X行第Y条要求"。这导致PRD要求在DD编写中被遗漏、偏移甚至违反，且无法自动发现。

---

## 二、P0 严重偏差（必须修复）

### P0-1: DD-01 前端伪代码使用Vue语法，违反PRD React强约束

| 维度 | 详情 |
|------|------|
| **PRD强约束** | 行1781: "React 18 + TypeScript + Vite" / 行2480: "react-router-dom（路由）" |
| **DD-01现状** | 行1036: `router.push("/login")` / 行1047: `router.beforeEach(async (to, from, next) =>` |
| **问题本质** | `router.push()` 和 `router.beforeEach()` 是 Vue Router 语法。React Router v6 使用 `useNavigate()` hook 和组件式路由守卫 |
| **影响范围** | DD-01 中所有前端伪代码（Token拦截器、路由守卫、登录跳转） |
| **修复方案** | 将所有前端伪代码改写为 React 18 + react-router-dom v6 语法 |

**示例修正**:

```pseudocode
# 错误 (Vue Router):
router.push("/login")
router.beforeEach(async (to, from, next) => { ... })

# 正确 (React Router v6):
navigate("/login")
# 路由守卫用 ProtectedRoute 组件包裹:
function ProtectedRoute({ children }) {
    const token = getAccessToken()
    if token is None then return <Navigate to="/login" />
    return children
end function
```

### P0-2: DD-03 五维评分函数4个缺失伪代码

| 维度 | 详情 |
|------|------|
| **PRD强约束** | 行228: "两个策略的粗筛结果取并集后，对每只候选股票计算多维度评分" / 行234-238: 评分维度权重明确 |
| **DD-03现状** | 5个评分函数中仅 `calculate_mainforce_score()` 有完整伪代码(行567-665)，其余4个仅有函数调用无实现 |
| **缺失函数** | `calculate_volume_price_score(klines)` — 量价20%权重 |
| | `calculate_fund_score(fund_flow)` — 资金25%权重(最高权重!) |
| | `calculate_sentiment_score(news, trade_date)` — 情绪15%权重 |
| | `calculate_capital_logic_score(candidate, news)` — 资本逻辑15%权重 |
| **影响** | 策略引擎核心逻辑缺失80%的评分算法，开发人员无法从DD直接编码 |
| **修复方案** | 补全4个评分函数的完整伪代码，包含输入字段→计算规则→输出分值映射 |

### P0-3: DD-03 vnpy回测适配层缺失（单标的 vs 全市场矛盾）

| 维度 | 详情 |
|------|------|
| **PRD强约束** | 行2515: "回测引擎 -- 选vnpy" / 行2435: "提取 backtesting.py + template.py + object.py + constant.py + utility.py" |
| **DD-03现状** | 行949: `vt_symbol = "all_stocks"` — 这不是vnpy合法参数 |
| **问题本质** | vnpy的 `BacktestingEngine` 设计为**单标的回测**（vt_symbol如"600519.SH"），而FraxVerse的策略是**全市场粗筛+评分**，两者架构根本不兼容 |
| **影响** | 伪代码无法执行，开发时必须重新设计回测架构 |
| **修复方案** | 设计 **FraxVerse回测适配层**: 方案A="逐标的回测+聚合统计"，方案B="自定义PortfolioBacktestingEngine继承vnpy基类"。需在DD-03中明确选型并写出适配层伪代码 |

---

## 三、P1 中等偏差（应修复）

### P1-1: `stock_pool.status` 列跨模块不一致

| 维度 | 详情 |
|------|------|
| **DD-02** | 行1190: `SELECT stock_code FROM stock_pool` — 查询无status条件 |
| **DD-03** | `stock_pool` 表DDL无 `status` 列 |
| **PRD要求** | 股票池应有活跃/失效状态区分 |
| **修复** | DD-03 的 `stock_pool` 表增加 `status VARCHAR(10) DEFAULT 'active'` 列，DD-02 的查询条件统一 |

### P1-2: `sector_constituents` 表缺失

| 维度 | 详情 |
|------|------|
| **DD-03** | 行433: `SELECT DISTINCT stock_code FROM sector_constituents` — 查询了一个不存在的表 |
| **DD-02** | 无此表DDL定义 |
| **PRD要求** | 策略二需要"板块成分股"数据，属于数据管理模块职责 |
| **修复** | DD-02 增加板块成分表DDL: `sector_constituents(sector_code, stock_code, weight, as_of_date)` |

### P1-3: 止损/止盈计算函数无伪代码

| 维度 | 详情 |
|------|------|
| **DD-03** | 行721-722: `calculate_stop_loss()` 和 `calculate_stop_profit()` 被调用但无实现 |
| **PRD要求** | 行640-651: 止损条件绑定、冷却期24小时、无绕过通道等详细规则 |
| **修复** | 在DD-03或DD-05中补全止损/止盈计算伪代码（含百分比止损、移动止盈、冷却期逻辑） |

### P1-4: 消息队列协议未指定

| 维度 | 详情 |
|------|------|
| **DD-03** | 使用 `[MQ] PUBLISH market:state_change` 等事件，但未定义MQ技术选型 |
| **PRD约束** | 行200: "Redis pub/sub通知各进程" / 行639: "Redis pub/sub通知新开仓" |
| **修复** | 明确消息队列使用 Redis Pub/Sub，并在DD-00或DD-03中定义消息格式(schema) |

### P1-5: `confidence` 字段计算未定义

| 维度 | 详情 |
|------|------|
| **DD-03** | `market_state_log` 表有 `confidence FLOAT` 列，但 `calculate_confidence()` 函数未实现 |
| **修复** | 定义市场状态置信度计算规则（如：粗筛命中数量/全市场股票数的比例） |

---

## 四、P2 改进建议

| # | DD文档 | 建议 |
|---|--------|------|
| P2-1 | DD-00 | 增加PRD需求追溯标记规范（见第六节方案） |
| P2-2 | DD-01 | 伪代码中增加PRD需求来源标注 |
| P2-3 | DD-02 | 实时价格缓存(`cache_realtime_prices`)的数据源未指定(miniQMT? AKShare?) |
| P2-4 | DD-03 | `market_cap_min/max` 参数名误导——实际用成交额代理，建议改名为 `daily_amount_min/max` 或增加 `total_mv` 列 |
| P2-5 | DD-03 | 无组合级风险约束（单票30%上限有，但无总仓位上限/板块集中度上限） |

---

## 五、根因分析：为什么会出现PRD→DD偏差

```
PRD (172项强约束)
  │
  │  ❌ 无追溯标记
  │  ❌ 无合规检查点
  │  ❌ 跨模块Schema无统一校验
  │
  ▼
DD编写（人脑记忆+手工对照）
  │
  │  → 遗漏PRD要求（如新闻采集复用StockAgent）
  │  → 偏移技术选型（如Vue替代React）
  │  → 跨模块不一致（如stock_pool.status）
  │  → 设计深度不均（如评分函数缺失）
  │
  ▼
实现代码（基于不完整的DD）
  │
  ▼
❌ 与PRD要求不符，返工成本高
```

**三大根因**:

1. **无追溯机制**: DD文档不标注"此设计来自PRD第X行"，无法反向验证覆盖完整性
2. **无Schema所有权校验**: 跨模块引用的表/字段没有"唯一权威定义者"机制，导致DD-02和DD-03对同一张表定义不同
3. **无编写检查清单**: 每个DD的编写者没有一份"PRD对本文档的强约束清单"作为编写前必读

---

## 六、根治方案：PRD需求追溯机制

### 方案概述

在DD-00中增加"需求追溯规范"，要求所有DD文档在关键设计决策处标注PRD来源。具体机制：

#### 6.1 PRD需求追溯矩阵

在详细设计目录下新建 `TRACE-MATRIX.md`，格式如下：

```markdown
| 追溯ID | PRD行号 | PRD原文摘要 | 约束级别 | 对应DD | DD章节 | 覆盖状态 |
|--------|---------|-------------|---------|--------|--------|---------|
| T-001 | L1781 | React 18 + TypeScript | 强 | DD-01 | 5.2 前端Token管理 | ✅已覆盖 |
| T-002 | L2512 | 新闻采集直接复用8源 | 强 | DD-02 | 4.3 新闻采集 | ✅已覆盖(V1.1) |
| T-003 | L228 | 5维评分+权重 | 强 | DD-03 | 4.2 评分引擎 | ⚠️部分覆盖 |
| ... | ... | ... | ... | ... | ... | ... |
```

**规则**:
- 每条PRD强约束(172项)必须出现在矩阵中
- 覆盖状态: ✅已覆盖 / ⚠️部分覆盖 / ❌未覆盖
- DD编写完成后，必须确保该DD对应的所有行均为 ✅

#### 6.2 DD文档内嵌追溯标记

在DD文档的关键设计决策处，增加PRD来源注释：

```pseudocode
# [PRD-T-054] 策略一粗筛：近60日跌幅>=20%
if decline_60d_pct >= 0.20 then  # PRD L207 强约束
    pass_coarse = true
end if
```

**格式**: `# [PRD-T-{追溯ID}]` 或 `# PRD L{行号} {强/软}约束`

#### 6.3 Schema所有权规则

```
规则1: 每张表有且仅有一个"权威定义DD"
规则2: 其他DD引用该表时，必须与权威定义一致
规则3: 新增列必须由权威DD作者确认

Schema所有权映射:
- users, sessions, system_config → DD-01 (权威)
- stocks, daily_klines, news, sector_data, sector_constituents → DD-02 (权威)
- stock_pool, market_state_log, strategy_params, backtest_results → DD-03 (权威)
- stop_loss_conditions, trade_orders, positions → DD-05 (权威)
- experiences, param_change_log → DD-07 (权威)
```

#### 6.4 DD编写前检查清单

每个DD编写前，从追溯矩阵中过滤出该DD对应的强约束，生成"必覆盖清单":

```markdown
## DD-05 编写前必覆盖清单 (来自PRD强约束)

- [ ] L593: 基于xtquant SDK实现
- [ ] L613: 订单失败自动重试(最多3次,间隔5秒)
- [ ] L620-622: 推进式仓位管理(50%+5%+补仓)
- [ ] L623: 摊平禁令
- [ ] L629: 止损监视器独立进程
- [ ] L640: 止损进程不读Agent分析结果
- [ ] L646: Agent无权干涉止损
- [ ] L647: 无绕过通道
- [ ] L648: 止损条件绑定为下单前提
- [ ] L649: 止损后24小时冷却期
- [ ] L651: 止损即时归档经验库
- [ ] L652: 内存缓存止损条件
- [ ] L698: 止盈为硬约束
- ... (共25项)
```

---

## 七、修复计划

### 第一优先级：修复现有P0偏差

| # | 修复项 | 目标文档 | 工作量估计 |
|---|--------|---------|-----------|
| 1 | 前端伪代码 Vue→React 改写 | DD-01 | 约40行伪代码改写 |
| 2 | 补全4个评分函数伪代码 | DD-03 | 约200-300行伪代码 |
| 3 | vnpy回测适配层设计+伪代码 | DD-03 | 约100行伪代码+架构说明 |

### 第二优先级：建立追溯机制（DD-04~08编写前必须完成）

| # | 修复项 | 目标文档 | 工作量估计 |
|---|--------|---------|-----------|
| 4 | 新建 TRACE-MATRIX.md | 详细设计目录 | 172行矩阵 |
| 5 | DD-00增加追溯规范章节 | DD-00 | 约50行 |
| 6 | Schema所有权映射写入DD-00 | DD-00 | 约30行 |

### 第三优先级：修复P1偏差

| # | 修复项 | 目标文档 |
|---|--------|---------|
| 7 | stock_pool 增加 status 列 | DD-03 |
| 8 | 新增 sector_constituents 表DDL | DD-02 |
| 9 | 补全止损/止盈计算伪代码 | DD-03 或 DD-05 |
| 10 | 明确消息队列为Redis Pub/Sub | DD-00 或 DD-03 |
| 11 | 定义 confidence 计算规则 | DD-03 |

---

## 附录：PRD强约束按DD分布统计

| DD文档 | 强约束数 | 软约束数 | 已审计 | P0偏差 | P1偏差 |
|--------|---------|---------|--------|--------|--------|
| DD-00 公共约定 | 10 | 0 | ✅ | 0 | 0 |
| DD-01 认证模块 | 17 | 2 | ✅ | 1 | 0 |
| DD-02 数据管理 | 16 | 5 | ✅ | 0(已修复) | 2 |
| DD-03 策略引擎 | 14 | 6 | ✅ | 2 | 3 |
| DD-04 AI-Agent | 20 | 5 | ❌待写 | - | - |
| DD-05 交易执行 | 25 | 5 | ❌待写 | - | - |
| DD-06 风险监控 | 14 | 5 | ❌待写 | - | - |
| DD-07 经验库 | 11 | 3 | ❌待写 | - | - |
| DD-08 前端交互 | 18 | 2 | ❌待写 | - | - |
| 跨模块 | 17 | 0 | - | - | - |
| **合计** | **172** | **33** | | **3** | **5** |

> **注**: DD-04~08尚未编写，故无法审计。建议在编写前先完成追溯机制建设。
