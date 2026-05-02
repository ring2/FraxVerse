# FraxVerse 移动端双主题设计系统 v3.0

> 作者：Hermes Agent（以顶尖 UI 设计师视角）
> 版本：3.0 · 基于设计稿 FraxVerse-V2-AllPages.html 精确还原
> 设计哲学：双主题对偶体系（Light：暖白手账 · Dark：星空投影）
> 适用：FraxVerse V2 移动端所有页面开发

---

## 0. 核心设计语言（Design Language）

### 0.1 品牌气质

FraxVerse 不是一个冰冷的量化工具，而是一个**交易者的修行道场**。

- **Light Mode** = 温暖通透的手账本。米白纸 `#FAF9F7`，紫墨水 `#7F77DD`，涨跌如珊瑚 `#E8735A` 点翠 `#4DB899`。亲和、有序、专注。
- **Dark Mode** = 夜晚的星空投影。深空 `#06060F` 做底，半透明紫水晶卡片叠加，信息浮在星尘之上。深邃、沉浸、不刺眼。

二者共享同一套组件骨骼，只是换了两套衣裳——不是两套设计。

### 0.2 双主题对偶原则

```
Light Mode (默认)                Dark Mode（可选）
────────────────────             ────────────────────
暖白基底                       深空基底
实色表面                       半透明玻璃质感卡片
微暖灰文字                     冷紫调文字
低透明度边框                   紫色调边框
柔和阴影                      更深阴影
珊瑚红涨 翡翠绿跌             提亮红涨 提亮绿跌
```

**关键设计决策**：Dark Mode 的卡片不是纯黑，而是 `rgba(15,15,35,0.85)`——保留 Light Mode 的「表面在上」感知，用半透明替代纯色。这让 Dark 不闷、不压抑。

### 0.3 移动端的差异化处理

与 PC 版的三个核心差异：

| 维度 | PC 版 | 移动端 |
|:-----|:------|:-------|
| 布局 | 侧栏 + Topbar + Content | 全屏容器 + 底部 Tab Bar |
| 信息密度 | 多列并列，4列指标网格 | 2列网格，渐进展开 |
| 交互 | 悬浮 hover、右键、快捷键 | Touch target ≥44px，手势滑动 |

---

## 1. 设计 Token 体系（精确到 CSS 变量）

### 1.1 Light Mode（默认主题）

```css
/* 直接从设计稿 :root 提取 */
--bg-page: #FAF9F7;              /* 页面基底——暖米白 */
--bg-surface: #FFFFFF;            /* 卡片/面板表面 */
--bg-sidebar: #F5F3EF;            /* 侧栏 */
--bg-sidebar-hover: #EDEAE4;      /* 侧栏悬浮 */
--bg-subtle: #F8F6F2;             /* 极浅背景（表格行、代码块）*/
--bg-elevated: #FFFFFF;           /* 弹窗/浮层 */

--purple-50: #F3F1FE;             /* 选中态/选中行 */
--purple-100: #E6E2FC;            /* 紫色 Tag 背景 */
--purple-200: #CECBF6;            /* 浅紫装饰线 */
--purple-400: #9B93E4;            /* 品牌亮紫（dot/装饰）*/
--purple-500: #7F77DD;            /* 品牌主紫（按钮/CTA）*/
--purple-600: #5F56C8;            /* 品牌深紫（hover）*/
--purple-700: #4A42A8;            /* 最深紫（文字）*/

--up: #E8735A;                    /* 涨/买入——暖珊瑚 */
--up-bg: #FEF2EF;                 /* 涨背景 */
--down: #4DB899;                   /* 跌/卖出——翡翠绿 */
--down-bg: #EFF9F5;               /* 跌背景 */
--amber: #E8A840;                  /* 中性/待审——琥珀 */
--amber-bg: #FFF8EB;               /* 琥珀背景 */

--text-primary: #2D2B28;          /* 主文字——深灰暖调 */
--text-secondary: #6B6760;        /* 次文字——灰褐 */
--text-tertiary: #9E9A92;         /* 辅助文字——浅褐 */
--text-inverse: #FFFFFF;          /* 反色文字 */

--border-light: rgba(0,0,0,0.06); /* 弱边框 */
--border-medium: rgba(0,0,0,0.10);/* 中边框 */

--shadow-card: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
--shadow-elevated: 0 4px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.03);

--logo-gradient: linear-gradient(135deg, #9B93E4, #5F56C8);
--btn-shadow: 0 2px 8px rgba(127,119,221,0.3);
--btn-shadow-hover: 0 4px 14px rgba(127,119,221,0.4);

--chart-grid: rgba(0,0,0,0.04);
--chart-line: #7F77DD;
```

### 1.2 Dark Mode（对照）

```css
--bg-page: #06060F;               /* 深空 */
--bg-surface: rgba(15,15,35,0.85);/* 半透明紫玻璃卡片 */
--bg-sidebar: rgba(6,6,15,0.7);
--bg-sidebar-hover: rgba(25,25,55,0.9);
--bg-subtle: rgba(10,10,26,0.6);
--bg-elevated: rgba(25,25,55,0.95);/* 弹窗 */

--purple-50: rgba(83,74,183,0.10);
--purple-100: rgba(83,74,183,0.15);
--purple-200: rgba(127,119,221,0.25);
--purple-400: #AFA9EC;
--purple-500: #7F77DD;
--purple-600: #AFA9EC;
--purple-700: #CECBF6;

--up: #F0997B;                    /* 涨——提亮 */
--up-bg: rgba(216,90,48,0.15);
--down: #5DCAA5;                   /* 跌——提亮 */
--down-bg: rgba(29,158,117,0.15);
--amber: #EF9F27;
--amber-bg: rgba(239,159,39,0.15);

--text-primary: #E0DFF0;
--text-secondary: #8887A8;
--text-tertiary: #5A5880;
--text-inverse: #06060F;
```

### 1.3 字体层级

| 角色 | Weight | Size (移动端) | 颜色 | 设计稿对照 |
|:-----|:-------|:--------------|:-----|:-----------|
| 页面标题 | 600 | 18px | --text-primary | h1 = 20px, 移动收窄 |
| 指标数值 | 600 | 22px | --text-primary | cell value |
| 指标小字 | 400 | 12px | --text-tertiary | metric-label |
| 卡片标题 | 500 | 13px | --text-primary | section-header |
| "更多"链接 | 500 | 12px | --purple-500 | section-action |
| 正文(表) | 400 | 13px | --text-primary | data-table td |
| 表头 | 400 | 11px | --text-tertiary | data-table th |
| 标签 | 500 | 11px | 语义色 | tag |
| 辅助 | 400 | 11-12px | --text-tertiary | form-hint |
| 顶栏/状态 | 500 | 12px | 语义色 | market-status |

字体栈：`Inter, 'Noto Sans SC', system-ui, -apple-system, BlinkMacSystemFont, sans-serif`

### 1.4 间距网格

基线：4px 网格。所有 margin/padding 必须是 4 的倍数（或 2px 微调）。

| 层级 | px | 用途 |
|:-----|:---|:-----|
| xs | 4px | 微间距 |
| sm | 8px | 元素间距、gap |
| md | 12px | 卡片/容器内边距（移动端） |
| lg | 16px | 段落间距 |
| xl | 20px | 区块间距 |
| 2xl | 24px | 页面内容上下边距 |

### 1.5 圆角体系

| Token | 值 | 用途 |
|:------|:---|:-----|
| --radius-sm | 6px | Tag、小元素、滚动条 |
| --radius-md | 10px | 按钮、输入框、普通卡片 |
| --radius-lg | 14px | 大卡片、section-card |
| --radius-xl | 20px | 登录面板、弹窗 |

---

## 2. 导航架构

### 2.1 底部 Tab Bar（5 Tab）

```
┌──────────────────────────────────────┐
│           Content Area               │
│           (flex: 1 overflow: auto)   │
│                                      │
├──────┬──────┬──────┬──────┬─────────┤
│ 📊   │ 💰   │ 🔄   │ 💎   │ ⚙️     │
│ 看盘  │ 股票池│ 交易  │ 更多  │ 设置    │
│ 仪表盘│ 股票池│ 持仓  │(抽屉)│ 系统配  │
└──────┴──────┴──────┴──────┴─────────┘
```

**Tab 配置**：

| Tab | Icon | 路由 | 设计稿映射 | 高亮指示器 |
|:----|:-----|:-----|:-----------|:-----------|
| 看盘 | CompassOutlined | /m/dashboard | 侧栏「仪表盘」 | 顶部 2px 紫线 |
| 股票池 | StarOutlined / AppstoreOutlined | /m/stock-pool | 侧栏「股票池」 | 同上 |
| 交易 | SwapOutlined | /m/trade | 侧栏「持仓管理」 | 同上 |
| 更多 | AppstoreOutlined + LayoutOutlined | /m/more | — | 同上 |
| 设置 | SettingOutlined | /m/settings | 侧栏底部「设置」 | 同上 |

**Tab Bar 参数**：
- 高度：56px + `env(safe-area-inset-bottom)`
- 背景 Light：`--bg-surface (#FFFFFF)` + `--border-light` 顶部分割线
- 背景 Dark：`--bg-sidebar (rgba(6,6,15,0.7))` + 紫色调分割线
- Tab 文字：inactive = `--text-tertiary`, active = `--purple-500`
- 当前 Tab 指示器：顶部 2px 紫色实线，宽度 24px，圆角 1px
- 点击反馈：无 hover 态，tap 时 opacity 0.7 闪缩

### 2.2 更多页面（💎 More）

"更多"是一个**抽屉式选项卡页**，容纳 6 个次要页面入口：

```
┌──────────────────────────────────────┐
│  更多                                │
│                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │  🧠  │  │  📖  │  │  🔔  │      │
│  │AI分析 │  │经验库 │  │ 通知  │      │
│  └──────┘  └──────┘  └──────┘      │
│                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │  📈  │  │  👁️  │  │  ⚡  │      │
│  │ 星轨  │  │ 天眼  │  │系统态 │      │
│  └──────┘  └──────┘  └──────┘      │
└──────────────────────────────────────┘
```

- 2×3 网格布局
- 每个入口：48px 圆形图标（品牌色渐变色背景）+ 12px 文字
- 卡片：74px × 74px，圆角 `--radius-lg`，边框 `--border-light`
- 点击跳转到对应页面（全屏推送，带右滑返回）

---

## 3. 组件规范（精确到设计稿）

> 所有组件值直接从设计稿提取。除非标记"移动端调整"，否则使用设计稿原始值。

### 3.1 指标卡片（metric-card）

**设计稿行 126-136**：

```
┌──────────────────┐
│ 总资产            │ ← metric-label: 12px --text-tertiary
│ ¥1,284,350       │ ← metric-value: 24px(PC)/22px(移动) --text-primary
│ ↑ 2.3% 今日      │ ← metric-change.up: 12px --up on --up-bg pill
└──────────────────┘
```

| 属性 | 值 |
|:-----|:---|
| 背景 | --bg-surface |
| 边框 | 1px solid --border-light |
| 圆角 | --radius-lg (14px) |
| padding | 18px（PC）/ 14px（移动） |
| 内顶部渐变线 | `linear-gradient(90deg,transparent,--purple-400,transparent)` 高 2px, opacity 0, hover→1 |
| hover 效果 | shadow-elevated + 边框变 --purple-100 + 顶部线出现 |
| 移动端网格 | 2 列 (grid-template-columns: 1fr 1fr) |
| gap | 12px（移动端） |

**设计稿精确复现**：
```html
<div class="metric-card">
  <div class="metric-label">总资产</div>
  <div class="metric-value">¥1,284,350</div>
  <div class="metric-change up">↑ 2.3% 今日</div>
</div>
```

**颜色变体**：
- `metric-value` 可染色：涨价用 `--up`，品牌指标用 `--purple-500`
- `metric-change` 分三类：`.up`（`--up` on `--up-bg`）、`.down`（`--down` on `--down-bg`）、中性（`--purple-400` on `--purple-50`）

### 3.2 区域卡片（section-card）

**设计稿行 138-139**：

```
┌──────────────────────────────────────┐
│ ● 今日交易信号          查看全部 →   │ ← section-header
├──────────────────────────────────────┤
│ 600519  贵州茅台  周期底部  92  ...  │ ← content area
│ ...                                  │
└──────────────────────────────────────┘
```

| 属性 | 值 |
|:-----|:---|
| 背景 | --bg-surface |
| 边框 | 1px solid --border-light |
| 圆角 | --radius-lg (14px) |
| header padding | 14px 18px |
| header border-bottom | 1px solid --border-light |
| content padding | 不定（视内容类型） |
| 整个卡片 hover | box-shadow: --shadow-card |

**section-title**：13px 500 `--text-primary`，左侧 `.dot` = 6px 紫色圆点 `--purple-400`
**section-action**：12px `--purple-500`，hover 时 `--purple-50` 背景

**移动端调整**：header padding 缩为 `12px 14px`，content padding 缩为 `6px 8px`

### 3.3 Tag 标签

**设计稿行 161-165**：

| 变体 | 背景 | 文字色 | 用途 |
|:-----|:-----|:-------|:-----|
| `tag-purple` | --purple-50: #F3F1FE | --purple-600: #5F56C8 | 策略标签、状态 |
| `tag-amber` | --amber-bg: #FFF8EB | --amber: #E8A840 | 中性/待审 |
| `tag-up` | --up-bg: #FEF2EF | --up: #E8735A | 涨/买入 |
| `tag-down` | --down-bg: #EFF9F5 | --down: #4DB899 | 跌/卖出/已成交 |

所有 Tag：font-size 11px, font-weight 500, border-radius 20px (pill), padding 2px 8px

### 3.4 按钮

**设计稿行 145-151**：

| 变体 | 样式 | 用途 |
|:-----|:-----|:-----|
| `btn-primary` | 渐变 `--purple-500 → --purple-600` + 白字 + `--btn-shadow` | CTA / 主要操作 |
| `btn-ghost` | 透明 + 1px solid `--border-medium` + `--text-secondary` | 次要操作 |
| `btn-danger` | `--up-bg` + `--up` 文字 | 危险操作 |

所有按钮：padding 6px 14px, border-radius --radius-md (10px), font-size 13px, font-weight 500

**移动端**：CTA 按钮宽 100%，高度 44px (touch target)，渐变色 + 阴影突出

### 3.5 数据表格

**设计稿行 154-158**：

| 元素 | 属性 |
|:-----|:-----|
| 表头 th | 11px 400 `--text-tertiary`, letter-spacing 0.3px, padding 9px 14px |
| 表体 td | 13px 400 `--text-primary`, padding 10px 14px |
| 行分割线 | 1px solid --border-light |
| 行悬浮 | `--bg-subtle` |
| 最后一行 | 无底部分割线 |
| 代码列 | font-weight 500（600519）|
| 涨跌列 | font-weight 500, 颜色 `--up`/`--down` |

**移动端处理**：表格在移动端必须可水平滑动。视口不足时包裹在 `overflow-x: auto` 容器中。首列固定为 sticky。

### 3.6 Agent 对话气泡

**设计稿行 176-193**：

| Agent | 左边框色 | 背景 | 头像颜色 | 名称色 |
|:------|:---------|:-----|:---------|:-------|
| 主线猎手 | --purple-400: #9B93E4 | --purple-50 | --purple-500 | --purple-600 |
| 资金侦探 | --down: #4DB899 | --down-bg | --down | --down |
| 情绪捕手 | --amber: #E8A840 | --amber-bg | --amber | --amber |
| 经验法官 | --text-tertiary | --bg-subtle | --text-tertiary | --text-secondary |

- padding: 10px 12px, border-radius: --radius-md, margin-bottom: 10px
- agent-name: 11px 500, agent-text: 12px `--text-secondary`, line-height 1.6
- avatar: 17px 圆形, 单字符, 白字

### 3.7 输入框与表单

**设计稿行 196-205, 257-260**：

| 元素 | Light | Dark |
|:-----|:------|:-----|
| 背景 | --bg-page: #FAF9F7 | --bg-page: #06060F (opacity层面) |
| 边框 rest | --border-medium | 同上 purple 调版 |
| 边框 focus | --purple-500 | --purple-500 |
| 圆角 | --radius-md (10px) | 同上 |
| padding | 9px 12px (内联) / 11px 14px (独立) | 同上 |
| 文字 | --text-primary | --text-primary |
| placeholder | --text-tertiary | --text-tertiary |

表单标签：12px 500 `--text-secondary`，margin-bottom 6px

### 3.8 Toggle Switch

**设计稿行 251-256**：

```
○───────●        OFF
─────●────        ON (紫色)
```

- 容器：40px × 22px, border-radius 11px
- 滑块：16px 圆形, 白色, left: 3px, transition
- OFF 态：`--border-medium` 背景
- ON 态：`--purple-500` 背景, 滑块 translateX(18px)
- 可抽象为 antd Switch: `color={colors.purple500}`, 但设计稿圆角更大

### 3.9 空状态

**设计稿行 214-216**：

```
          🗂️
     暂无数据
  (可选说明文字)
```

- 居中, padding 60px 20px
- 图标: 48px, `--text-tertiary`, opacity 0.5
- 文字: 13px `--text-tertiary`

### 3.10 Toast（轻提示）

**设计稿行 223-224**：

- 固定顶部居中, translateX(-50%)
- 背景 `--bg-surface`, 边框 `--border-medium`, 圆角 `--radius-lg`
- 阴影 `--shadow-elevated`
- 入场动画: translateY(-80px) → translateY(0), opacity 0→1, 0.4s cubic-bezier
- 出场: 反向
- 非阻塞, 1.8s 自动消失

---

## 4. 页面布局树（全量）

### 4.1 App Shell

```
<MobileLayout>
  ├── TopBar (56px, --bg-surface, border-bottom)
  │   ├── 返回按钮 (仅二级页面)
  │   ├── 页面标题 (18px 600 --text-primary)
  │   ├── Spacer
  │   └── 右侧操作区 (市场状态 Tag / 更多按钮)
  │
  ├── Content (flex: 1, overflow: auto, padding: 12px)
  │   ├── 页面标题栏 (可选)
  │   ├── 指标卡片网格 (2列)
  │   ├── 区域卡片 (section-card)
  │   ├── 表格 / 列表
  │   └── 空态 / 加载态 / 错误态
  │
  └── TabBar (56px + safe-area-inset-bottom)
      ├── 📊 看盘
      ├── 💰 股票池
      ├── 🔄 交易
      ├── 💎 更多
      └── ⚙️ 设置
```

### 4.2 页面路由表

| 页面 | 路由 | Tab归属 | TopBar | 数据来源 |
|:-----|:-----|:--------|:-------|:---------|
| 看盘 | /m/dashboard | 📊 看盘 | 页面标题 + 市态Tag | portfolio + market API |
| 股票池 | /m/stock-pool | 💰 股票池 | 页面标题 | stockPool API |
| 交易 | /m/trade | 🔄 交易 | 页面标题 | trade + positions API |
| 更多 | /m/more | 💎 更多 | "更多"标题 | — |
| 设置 | /m/settings | ⚙️ 设置 | "设置"标题 | config API |
| AI分析 | /m/ai | 💎→子页 | 返回+标题 | agent API |
| 经验库 | /m/experience | 💎→子页 | 返回+标题 | experience API |
| 通知 | /m/notifications | 💎→子页 | 返回+标题 | notification API |
| 星轨(资产) | /m/equity | 💎→子页 | 返回+标题 | equity API |
| 天眼(监控) | /m/monitor | 💎→子页 | 返回+标题 | monitor API |
| 系统状态 | /m/system | 💎→子页 | 返回+标题 | health API |

### 4.3 页面状态机器（通用）

每个数据页面统一遵循：

```
API fetch → loading → empty / error / normal
```

| 状态 | 视觉表现 |
|:-----|:---------|
| **loading** | 居中 Spin（antd），背景 `--bg-page`，提示文字"加载中..." |
| **empty** | 居中空状态组件（图标 + "暂无XX"）|
| **error** | 错误简文 + "重新加载" 按钮（btn-primary 变体）|
| **normal** | 正常数据展示 |
| **offline** | 顶部轻提示横幅（非阻塞）|

---

## 5. 交互动效

### 5.1 主题切换动画

设计稿专门实现了主题切换 Toast + CSS transition：

```
[data-theme] { transition: background .35s, color .35s; }
```

Touch 主题切换按钮 → 立即切换 CSS 变量 → 所有元素过渡 350ms → Toast 提示当前主题

Dark Mode 粒子系统同步升级：base-opacity 从 0.15 → 0.25，新增 glow 效果

### 5.2 页面过渡

- **Tab 切换**：无动画，直接替换（避免用户等待）
- **二级页面 push**：右滑入场（translateX 100% → 0, 300ms ease-out）
- **二级页面 pop**：左滑出场或右滑手势返回

### 5.3 微交互

| 元素 | 交互 | 参数 |
|:-----|:-----|:-----|
| Tab 点击 | active 文字变色 + 顶部指示器出现 | 200ms ease |
| 卡片点击/悬浮 | 轻微上浮 + 边框变紫 + 顶部渐变线出现 | 250ms ease |
| 按钮点击 | 按压缩小 (transform: scale(0.97)) + 阴影加深 | 150ms ease |
| 列表行点击 | 背景变 --bg-subtle | 150ms |
| Toast 出现/消失 | 上滑入场 + 渐变 | 400ms cubic-bezier(.4,0,.2,1) |
| 数值刷新 | 数字变化眨眼 (opacity 0→1, 200ms) | 仅首次加载 |

---

## 6. 当前项目状态与实施策略

### 6.1 现实检查

| 项目 | 当前状态 | 目标 |
|:-----|:---------|:-----|
| colors.ts | 仅深色（深空紫+碎片蓝） | 双主题 CSS Variables |
| fraxTheme.ts | 仅 darkAlgorithm | 动态切换 |
| MobileLayout | 4 Tab，硬编码深色 | 5 Tab，双主题 |
| 移动页面 | 4 个页面，antd Card/Statistic | 设计稿精确组件 |
| 双主题切换 | 未实现 | 完整的 Light/Dark 切换 |

### 6.2 分阶段实施

```
阶段一（P0.5 — 本次）：
  └─ 让移动端 UI 精确对齐设计稿双主题规范
  ├─ 重构 colors → theme.ts：双主题 CSS Variables + 类型安全
  ├─ MobileLayout：5 Tab + 双主题可切换
  ├─ 重写 4 个主页面：对齐设计稿 metric-card / section-card 组件
  ├─ 新建 6 个子页面架构（路由 + 骨架）
  └─ 双主题切换：内存 level，通过 ThemeContext 分发

阶段二（P1）：
  ├─ CSS Variables 注入 HTML 实现系统级切换
  ├─ 持久化到 localStorage + 跟随系统偏好
  └─ antd ConfigProvider 动态切换算法
```

---

## 7. 工程约束

### 7.1 代码规范

- **使用 inline style**（维持现有模式），不新建 CSS 文件
- **双主题通过 ThemeContext 分发**，所有颜色值引用 context，而非 `colors.ts`
- 组件类型：`React.FC` 或 function component（无 class component）
- 使用 `App.useApp()` 获取 `message`/`notification`/`modal`
- 后端接口失败时使用 fallback mock 数据（不接受白屏或 500）
- 构建标准：`tsc --noEmit` 零错误 + `npm run build` 通过

### 7.2 主题上下文结构

```typescript
interface FraxTheme {
  mode: 'light' | 'dark';
  // 以下所有值按双主题注入
  bg: { page: string; surface: string; sidebar: string; subtle: string };
  purple: { 50: string; 100: string; 200: string; 400: string; 500: string; 600: string; 700: string };
  semantic: { up: string; upBg: string; down: string; downBg: string; amber: string; amberBg: string };
  text: { primary: string; secondary: string; tertiary: string; inverse: string };
  border: { light: string; medium: string };
  shadow: { card: string; elevated: string };
  gradient: { logo: string; btn: string };
  radius: { sm: number; md: number; lg: number; xl: number };
}
```

### 7.3 响应式断点

| 断点 | 范围 | 布局变化 |
|:-----|:-----|:---------|
| xs | < 375px | 极紧凑，隐藏辅助文字 |
| sm | 375-414px | iPhone 标准，正常显示 |
| md | 414-768px | 大屏手机，略宽松 |
| lg | > 768px | 不属移动端设计范围 |

---

## 8. 设计质检清单

每个页面交付前核对：

- [ ] 页面标题层级对齐设计稿（18px 600 头部，13px 500 卡片标题）
- [ ] 指标卡片圆角 14px，边框 1px solid --border-light
- [ ] Tag 使用正确变体（purple/amber/up/down），圆角 20px pill
- [ ] 涨跌色正确（Light: 珊瑚红翡翠绿, Dark: 提亮版）
- [ ] 按钮渐变是否使用 logo-gradient 规格
- [ ] Dark Mode 半透明卡片参数正确 (rgba(15,15,35,0.85))
- [ ] 间距基于 4px 网格
- [ ] Touch target ≥ 44px
- [ ] Loading/empty/error 三态俱全
- [ ] 双主题切换后所有颜色正确切换

---

## 9. 参考

- **设计稿**: `/home/ubuntu/FraxVerse/docs/设计稿/FraxVerse-V2-AllPages.html`（1360行，14页面）
- **PC 主题**: `/home/ubuntu/FraxVerse/frontend/src/theme/colors.ts` + `fraxTheme.ts`
- **移动端布局**: `/home/ubuntu/FraxVerse/frontend/src/components/layout/MobileLayout.tsx`
- **现有页面**: MobileDashboard.tsx, MobileStockPool.tsx, MobileTrade.tsx, MobileSettings.tsx
- **路由**: `/home/ubuntu/FraxVerse/frontend/src/App.tsx`
