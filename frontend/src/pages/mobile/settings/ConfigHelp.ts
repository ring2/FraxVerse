export type ConfigHelp = {
  scene: string;
  detail?: string;
  defaultVal?: string;
  recommend?: string;
};

export const CONFIG_HELP: Record<string, ConfigHelp> = {
  // ── 我的账户 ──
  session_timeout: {
    scene: "系统检测到无操作后自动登出，保护账户安全。盘中盯盘时如果设置了太短会频繁被踢。",
    defaultVal: "30",
    recommend: "30-120",
  },

  // ── AI 模型 ──
  llm_timeout: {
    scene: "Agent 调用 AI 模型的最大等待时间。如果模型响应慢（如高峰期 API 延迟高），超时后会自动重试。",
    defaultVal: "60",
    recommend: "30-120",
  },
  llm_max_concurrent: {
    scene: "同时向 AI 模型发起请求的最大数量。开多个 Agent 同时分析多个股票时需要更高的并发。注意 API 限频。",
    defaultVal: "8",
    recommend: "4-16",
  },
  llm_monthly_token_limit: {
    scene: "控制 AI 调用的月度 token 消耗上限，防止某一个月份因为特殊行情导致 API 费用暴增。",
    defaultVal: "不限",
    recommend: "根据预算设定",
  },
  agent_discussion_rounds: {
    scene: "Agent 内部多轮讨论的轮数。轮数越多分析越深入，但消耗更多 token、响应更慢。通常 2 轮足够平衡效率和质量。",
    defaultVal: "2",
    recommend: "1-3",
  },
  agent_convergence_threshold: {
    scene: "Agent 多轮讨论后，意见分歧小于此值就视为收敛、停止讨论。值越小越严格、讨论时间越长。",
    defaultVal: "0.3",
    recommend: "0.1-0.5",
  },

  // ── 交易策略 ──
  strategy_bottom_days: {
    scene: "「周期底部量能异动」策略核心参数。股价在此时间区间内的最大回撤超过一定阈值，系统认为进入了底部区域。天数越大，信号越可靠，但候选越少。",
    detail: "系统在过去 N 个交易日中计算最高点到最低点的跌幅，超过阈值则标记为底部候选，再检查量能异动和板块共振。",
    defaultVal: "60",
    recommend: "40-90",
  },
  strategy_bottom_decline_pct: {
    scene: "底部判定跌幅阈值。股价从近期高点跌到此幅度以上，系统认为可能进入底部区域。",
    detail: "结合 strategy_bottom_days 使用：近 60 日跌幅超过 20% → 底部候选。值越小越容易触发信号，但假信号越多。",
    defaultVal: "20",
    recommend: "15-30",
  },
  strategy_bottom_crash_pct: {
    scene: "「暴力下杀」检测阈值。近期（5日）内跌幅超过此值，系统认为出现恐慌性抛售，可能迎来反转。",
    detail: "S1 策略的二次筛选条件：在底部候选股中，5 日内急跌超过此值，信号优先级提高。",
    defaultVal: "5",
    recommend: "3-8",
  },
  strategy_bottom_min_klines: {
    scene: "底部区域判断需要的最少 K 线数量。新股上市不足此数量时跳过底部策略评估。",
    defaultVal: "30",
    recommend: "20-60",
  },
  strategy_sector_concentration: {
    scene: "「主线板块判定」阈值。板块内符合条件的股票数量超过此比例，系统认为该板块是市场主线，给板块内个股加分。",
    defaultVal: "12",
    recommend: "8-20",
  },
  strategy_sector_check_days: {
    scene: "板块持续性检查天数。板块连续 N 天保持热度才认定为是主线，防止一日游行情误导。",
    defaultVal: "2",
    recommend: "2-5",
  },
  strategy_adx_threshold: {
    scene: "S2（趋势动量低吸）策略关键参数。ADX 低于此值视为震荡行情，不触发趋势策略信号。ADX 越高趋势越强。",
    defaultVal: "25",
    recommend: "20-30",
  },
  strategy_shrink_ratio: {
    scene: "缩量回调检测阈值。回调时成交量萎缩到前期均量的一定比例以下，说明抛压枯竭，是低吸的好时机。",
    detail: "设 80%：回调日成交量 < 前 20 日均量的 80% → 缩量信号。值越小要求缩量越极致。",
    defaultVal: "80",
    recommend: "60-90",
  },
  strategy_momentum_drop_pct: {
    scene: "「趋势动量低吸」策略的买入候选条件。短期均线跌破一定比例后系统开始关注，寻找回调到支撑位的介入机会。",
    defaultVal: "3",
    recommend: "2-5",
  },
  strategy_momentum_min_amount: {
    scene: "趋势策略的最低成交额门槛。低于此成交量的股票流动性不足，不纳入策略范围。",
    defaultVal: "3 亿",
    recommend: "1-5 亿",
  },
  strategy_momentum_min_klines: {
    scene: "趋势策略要求的最少 K 线数。上市时间太短的股票趋势数据不足，跳过评估。",
    defaultVal: "66",
    recommend: "60-120",
  },
  strategy_stop_loss_pct: {
    scene: "开仓时自动设置的默认止损偏移。买入后股价从成本价下跌到此比例时触发止损。各股票也可在开仓时单独指定。",
    detail: "止损优先级：开仓时指定值 > 策略默认值。",
    defaultVal: "5",
    recommend: "3-8",
  },
  strategy_take_profit_pct: {
    scene: "开仓时自动设置的默认止盈偏移。股价上涨到此比例后触发分批止盈：第一档卖 30%，第二档卖 40%，第三档开始移动止盈。",
    defaultVal: "10",
    recommend: "8-20",
  },
  strategy_max_positions: {
    scene: "系统同时持仓的最大股票数量。超过此数新信号不生成开仓决策。实盘建议 3-5 只，兼顾集中度和分散风险。",
    defaultVal: "3",
    recommend: "3-5",
  },

  // ── 风控 ──
  risk_daily_max_drawdown: {
    scene: "单日最大可承受的总资产回撤比例。触发后系统自动降半仓，暂停新开仓，防止单日亏损扩大。",
    detail: "盘中持续监控总资产，从当日最高点回撤超过此比例时，风控系统立即启动降仓流程。",
    defaultVal: "5",
    recommend: "3-8",
  },
  risk_extreme_drawdown: {
    scene: "极端回撤阈值。总资产从最高点回撤超过此比例时，系统执行一键清仓。这是最后一道防线。",
    detail: "与 daily_max_drawdown 的区别：单日回撤触发降仓，连续回撤或黑天鹅导致累计回撤达到此值 → 一键清仓。",
    defaultVal: "8",
    recommend: "8-15",
  },
  risk_max_consecutive_losses: {
    scene: "连续亏损次数阈值。策略连续亏损达到此次数时自动暂停，防止恶性循环。暂停后需人工分析原因后手动开启。",
    detail: "行为金融学中的冷却机制，避免「越亏越操作」。",
    defaultVal: "5",
    recommend: "3-5",
  },
  risk_single_position_limit: {
    scene: "单只股票占总资产的最大仓位比例。防止某一支票过度集中，暴雷时损失可控。",
    defaultVal: "30",
    recommend: "20-40",
  },
  risk_factor_crowding: {
    scene: "因子拥挤度阈值。同质化策略太多时因子超额收益迅速衰减。超过此阈值系统降低该因子权重。",
    defaultVal: "48",
    recommend: "40-60",
  },
  risk_extreme_market_decline: {
    scene: "大盘极端行情判定阈值。上证指数单日跌幅超过此值时进入极端行情模式：暂停买入、加大止损幅度。",
    defaultVal: "5",
    recommend: "3-5",
  },

  // ── 交易执行 ──
  trade_commission_rate: {
    scene: "券商佣金费率（万分之）。用于计算每笔交易佣金成本，影响净盈亏。默认万 3。",
    defaultVal: "3",
    recommend: "1-5",
  },
  trade_stamp_tax_rate: {
    scene: "印花税率（千分之）。A 股卖出时收取，当前政策为千分之一。",
    defaultVal: "1",
    recommend: "0.5-1",
  },
  trade_slippage: {
    scene: "预期滑点（跳）。实际成交价与触发价之间的偏差，流动性越差的股票滑点越大。",
    defaultVal: "1",
    recommend: "1-3",
  },

  // ── 数据与通知 ──
  datasource_qmt_host: {
    scene: "miniQMT 的 IP 地址。实盘模式下必须正确配置，否则无法获取实时行情和下单。",
    defaultVal: "127.0.0.1",
    recommend: "局域网 IP",
  },
  datasource_qmt_port: {
    scene: "miniQMT 的服务端口。与 miniQMT 客户端设置的端口一致。",
    defaultVal: "8001",
    recommend: "8001-8010",
  },
  datasource_sync_time: {
    scene: "每日收盘后自动同步数据的时间。建议 15:30（A 股收盘后半小时），此时数据基本稳定。",
    defaultVal: "15:30",
    recommend: "15:30-16:00",
  },
  datasource_news_poll_interval: {
    scene: "舆情数据轮询间隔（分钟）。越短获取新闻越快，但增加服务器负载。盘中建议 5 分钟。",
    defaultVal: "10",
    recommend: "5-30",
  },
  news_collect_interval: {
    scene: "新闻采集间隔时间。与舆情轮询的区别：这是定时采集上游源的时间，后者是推送间隔。",
    defaultVal: "10",
    recommend: "5-30",
  },
  news_max_retention: {
    scene: "新闻最多保留条数。超过此数自动清理最旧的，防止数据库膨胀。",
    defaultVal: "200",
    recommend: "100-500",
  },
  news_hot_keywords: {
    scene: "热点关键词列表，逗号分隔。匹配的新闻标记为「热点」，在日报和推送中优先展示。",
    defaultVal: "空",
    recommend: "输入你关注的题材，如：算力、低空经济、机器人",
  },

  // ── 复核配置 ──
  review_high_open_cancel_pct: {
    scene: "开盘前复核：目标股票高开超过此比例，自动取消买入计划。防止追高被套。",
    detail: "开盘前 5 分钟读取集合竞价结果，对计划买入操作复核。高开 = 买在情绪高点，容易套人。",
    defaultVal: "3",
    recommend: "2-5",
  },
  review_low_open_cancel_pct: {
    scene: "开盘前复核：目标股票低开超过此比例，取消买入计划。低开太多可能是有未公开的利空。",
    defaultVal: "3",
    recommend: "3-5",
  },
  review_overseas_volatility_pct: {
    scene: "外盘波动复核阈值。隔夜美股或 A50 期货波动超过此值时，开盘前触发复核流程。",
    defaultVal: "2",
    recommend: "1-3",
  },

  // ── 经验库 ──
  experience_decay_months: {
    scene: "经验随时间衰减的周期。超过此时间的经验权重逐渐下降，因为市场环境变了。",
    defaultVal: "6",
    recommend: "3-12",
  },
  experience_archive_months: {
    scene: "未验证的旧经验超过此时间自动归档。归档后不再参与决策匹配，但保留供查看。",
    defaultVal: "12",
    recommend: "6-24",
  },
  experience_weight_market: {
    scene: "经验匹配时「市场状态」维度的权重占比。4 个权重按比例分配，总和建议 100%。",
    defaultVal: "30",
    recommend: "25-40",
  },
  experience_weight_sector: {
    scene: "经验匹配时「板块属性」维度的权重占比。板块越匹配越优先采用。",
    defaultVal: "25",
    recommend: "20-35",
  },
  experience_weight_tech: {
    scene: "经验匹配时「技术形态」维度的权重占比。K 线形态与当前走势的相似度权重。",
    defaultVal: "25",
    recommend: "20-30",
  },
  experience_weight_fund: {
    scene: "经验匹配时「资金特征」维度的权重占比。资金流向、主力行为匹配度权重。",
    defaultVal: "20",
    recommend: "15-25",
  },

  // ── 系统 ──
  log_level: {
    scene: "日志输出级别。DEBUG 最多（含 SQL）、INFO 正常、WARNING 减少输出。调试时切 DEBUG。",
    defaultVal: "INFO",
    recommend: "INFO（日常）/ DEBUG（调试）",
  },
  rate_limit: {
    scene: "全局限流：每 IP 每秒最多请求数。防止恶意访问和频繁调用拖垮服务。",
    defaultVal: "60",
    recommend: "30-120",
  },
  backup_time: {
    scene: "每日自动备份时间。建议凌晨低负载时段。",
    defaultVal: "03:00",
    recommend: "02:00-04:00",
  },
  backup_retention_days: {
    scene: "备份保留天数。超过此时间的旧备份自动删除，防止磁盘占满。",
    defaultVal: "7",
    recommend: "7-30",
  },
  particle_effect: {
    scene: "开启/关闭背景粒子动画。关闭可减少 CPU 和电池消耗，移动端建议关闭。",
    defaultVal: "开",
    recommend: "移动端建议关闭",
  },
};
