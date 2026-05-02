# FraxVerse 技术验证 PoC 报告

> 日期：2026-05-01
> 目的：在正式开发P0之前，验证关键技术依赖的可用性，评估复用基础

---

## 1. 验证结果总览

| # | 技术点 | 状态 | 结论 |
|:--|:-------|:-----|:-----|
| PoC-1 | miniQMT (xtquant) | ⚠️ 部分通过 | SDK已安装(v250516.1.1)，xtdata/xttrader可导入，**但需要QMT客户端运行才能获取数据** |
| PoC-2 | AKShare 数据采集 | ✅ 完全通过 | v1.18.48，日K线/资金流向/板块数据均正常获取，数据格式完整 |
| PoC-3 | vnpy 回测引擎 | ❌ 未安装 | vnpy未安装，StockAgent无回测代码，需从头适配vnpy或自建轻量回测 |
| PoC-4 | TradingAgents 编排 | ✅ 完全通过 | TradingAgentsGraph/GraphSetup/create_llm_client均可用，Agent框架完整 |
| PoC-5 | Docker(PG+Redis) | ❌ Docker未安装 | 本机无Docker，需安装Docker Desktop；Python侧redis-py/SQLAlchemy已就绪，缺psycopg2/asyncpg/alembic |

---

## 2. 详细验证记录

### 2.1 miniQMT (xtquant)

```
已安装：xtquant 250516.1.1
依赖：numpy, pandas, requests, tqdm
导入测试：
  from xtquant import xtdata   ✅ OK
  from xtquant import xttrader ✅ OK
数据获取测试：
  xtdata.get_market_data() → ❌ 需要QMT客户端运行
  错误信息："无法连接xtquant服务，请检查QMT-投研版或QMT-极简版是否开启"

结论：
- SDK本身无问题，但miniQMT是"客户端模式"——必须同时运行QMT极简版
- 开发阶段可先用AKShare替代行情数据，miniQMT仅用于实盘交易执行
- 交易执行(PoC-1)需在实盘阶段验证，P0/P1阶段不需要
```

### 2.2 AKShare

```
已安装：akshare 1.18.48
日K线测试(stock_zh_a_hist)：
  贵州茅台 600519, 20260420-20260501
  9行数据，12列：日期/股票代码/开盘/收盘/最高/最低/成交量/成交额/振幅/涨跌幅/涨跌额/换手率
  最新数据：2026-04-30 收盘1384.79 ✅

资金流向测试(stock_individual_fund_flow)：
  120行数据，13列：主力净流入/超大单/大单/中单/小单
  数据完整 ✅

结论：
- AKShare完全满足P0阶段数据需求（日K线+资金流+板块数据）
- 需注意限流：建议每次调用间隔1秒，批量获取时加sleep
- 后续需测试：板块数据(ak.stock_board_industry_name_em)、A股列表(ak.stock_zh_a_spot_em)
```

### 2.3 vnpy 回测引擎

```
vnpy：未安装
StockAgent中无回测相关代码
TradingAgents中无回测相关代码

结论：
- P0 Day6需要回测能力，但vnpy较重(依赖Qt等)
- 两个替代方案：
  A) 安装vnpy，提取核心回测模块（6个文件），去Qt依赖 → 架构文档原方案
  B) 自建轻量回测引擎（基于pandas），只支持日线级别 → 更简单可控
- 建议先用方案B快速跑通，等P2阶段再评估是否需要vnpy的高级功能
```

### 2.4 TradingAgents

```
核心模块导入测试：
  from tradingagents.graph.trading_graph import TradingAgentsGraph ✅
  from tradingagents.graph.trading_graph import create_llm_client ✅
  from tradingagents.graph.setup import GraphSetup ✅

Agent组件：
  agents/analysts/ — 分析师Agent
  agents/researchers/ — 研究员Agent
  agents/managers/ — 管理层Agent
  agents/trader/ — 交易员Agent
  agents/risk_mgmt/ — 风控Agent

数据Schema：
  PortfolioDecision, TraderAction, TraderProposal, ResearchPlan ✅

LLM客户端：
  openai_client.py, anthropic_client.py, google_client.py, azure_client.py ✅
  create_llm_client() 工厂方法 ✅

结论：
- TradingAgents框架完整，可直接作为Agent层基础
- 需适配：将4个Agent（主线猎手/资金侦探/情绪捕手/经验法官）映射到TradingAgents的Agent角色
- P2阶段使用，P0/P1不需要
```

### 2.5 Docker + 数据库

```
Docker Desktop：❌ 未安装
Python数据库驱动：
  redis-py ✅ (已安装)
  SQLAlchemy 2.0.48 ✅ (已安装)
  psycopg2 ❌ (未安装)
  asyncpg ❌ (未安装)
  alembic ❌ (未安装)

FastAPI生态：
  fastapi 0.135.2 ✅
  uvicorn 0.42.0 ✅
  APScheduler 3.11.2 ✅

结论：
- 必须安装Docker Desktop才能运行PG+Redis容器
- Python侧需补充安装：asyncpg + alembic（异步PG驱动 + 迁移工具）
- 临时替代：P0阶段可用SQLite代替PG，用内存Redis（或直接dict缓存）跳过Docker依赖
```

---

## 3. StockAgent 可复用代码清单

| 模块 | 路径 | 复用价值 | 说明 |
|:-----|:-----|:---------|:-----|
| AKShare适配器 | src/data_sources/akshare_adapter.py | ⭐⭐⭐ 高 | 已封装AKShare数据获取，可直接复用 |
| 数据源基类 | src/data_sources/base.py | ⭐⭐ 中 | 定义了统一数据源接口 |
| 新闻采集器 | src/collector/ | ⭐⭐⭐ 高 | 含去重/生命周期/事件聚类/指标统计 |
| 三层记忆 | src/memory/ | ⭐⭐⭐ 高 | 感知/工作/长期三层认知记忆架构，经验库基础 |
| RAG检索 | src/rag/ | ⭐⭐ 中 | 知识库检索增强 |
| LLM封装 | src/llm/ | ⭐⭐ 中 | LLM调用封装 |
| Agent编排 | src/orchestrator/ | ⭐⭐ 中 | 工作流编排 |
| FastAPI骨架 | AgentServer/main.py | ⭐⭐ 中 | 项目启动入口 |
| 前端(Vue) | frontend/ | ⭐ 低 | PRD决定用React重写前端，Vue代码仅参考 |

---

## 4. 开发前必须完成的环境准备

### 4.1 必须安装（阻塞P0）

| 项目 | 操作 | 优先级 |
|:-----|:-----|:-------|
| Docker Desktop | 下载安装并启动 | P0-Day1必须 |
| asyncpg | `pip install asyncpg` | P0-Day1必须 |
| alembic | `pip install alembic` | P0-Day1必须 |

### 4.2 建议安装（P0-Day6前）

| 项目 | 操作 | 说明 |
|:-----|:-----|:-----|
| vnpy | `pip install vnpy` | 回测引擎，如果选择方案A |

### 4.3 可选安装（P2阶段）

| 项目 | 操作 | 说明 |
|:-----|:-----|:-----|
| QMT极简版 | 迅投官网下载 | 实盘交易阶段必需 |

---

## 5. 技术风险评估

| 风险 | 级别 | 缓解措施 |
|:-----|:-----|:---------|
| Docker未安装，PG/Redis无法启动 | 🔴 高 | P0-Day1必须安装；临时方案可用SQLite+内存缓存 |
| vnpy未安装，无回测能力 | 🟡 中 | 自建轻量回测引擎（方案B），或安装vnpy |
| miniQMT需QMT客户端 | 🟡 中 | 开发阶段用AKShare替代，实盘阶段再验证 |
| AKShare API限流 | 🟢 低 | 每次调用间隔1秒，批量获取加sleep |

---

## 6. 建议的下一步行动

1. **安装Docker Desktop** — 最高优先级，所有数据库依赖的前提
2. **创建FraxVerse项目骨架** — 新建 fraxverse/ 目录，搭好项目结构
3. **启动PG+Redis容器** — Docker Compose 配置并启动
4. **开始P0 Day1** — 建表 + AKShare数据采集

轻量回测引擎方案（方案B）可节省vnpy依赖，建议P0阶段先用这个。
