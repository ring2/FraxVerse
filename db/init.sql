1|-- FraxVerse 碎片宇宙量化系统 · 数据库初始化脚本
     2|-- 来源：DD-01 ~ DD-09 详细设计文档（自动提取）
     3|-- 版本：V1.0
     4|
     5|CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
     6|SET search_path TO public;
     7|
     8|CREATE TABLE stocks (
     9|    code            VARCHAR(10)     PRIMARY KEY,       -- 股票代码，如 600519.SH
    10|    name            VARCHAR(20)     NOT NULL,           -- 股票名称
    11|    industry        VARCHAR(30),                        -- 所属行业
    12|    market          VARCHAR(10)     NOT NULL,           -- SH/SZ/BJ
    13|    list_date       DATE,                               -- 上市日期
    14|    is_st           BOOLEAN         NOT NULL DEFAULT FALSE,  -- 是否ST
    15|    is_suspended    BOOLEAN         NOT NULL DEFAULT FALSE,  -- 是否停牌
    16|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
    17|);
    18|CREATE INDEX idx_stocks_st ON stocks(is_st) WHERE is_st = TRUE;
    19|CREATE INDEX idx_stocks_suspended ON stocks(is_suspended) WHERE is_suspended = TRUE;
    20|CREATE INDEX idx_stocks_industry ON stocks(industry);
    21|COMMENT ON TABLE stocks IS 'A股基本信息表，约5000行';
    22|
    23|CREATE TABLE daily_klines (
    24|    id              BIGSERIAL       PRIMARY KEY,
    25|    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    26|    trade_date      DATE            NOT NULL,
    27|    open            NUMERIC(10,2)   NOT NULL,           -- 开盘价
    28|    high            NUMERIC(10,2)   NOT NULL,           -- 最高价
    29|    low             NUMERIC(10,2)   NOT NULL,           -- 最低价
    30|    close           NUMERIC(10,2)   NOT NULL,           -- 收盘价
    31|    volume          BIGINT          NOT NULL,            -- 成交量（股）
    32|    amount          NUMERIC(18,2)   NOT NULL,            -- 成交额（元）
    33|    turnover_rate   NUMERIC(8,4),                       -- 换手率
    34|    adjust_flag     VARCHAR(10)     NOT NULL DEFAULT 'none',  -- none/front/back
    35|    ma5             NUMERIC(10,2),
    36|    ma10            NUMERIC(10,2),
    37|    ma20            NUMERIC(10,2),
    38|    ma60            NUMERIC(10,2),
    39|    adx             NUMERIC(8,4),
    40|    cmf             NUMERIC(10,6),
    41|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    42|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    43|    UNIQUE(stock_code, trade_date, adjust_flag)
    44|);
    45|CREATE INDEX idx_klines_code_date ON daily_klines(stock_code, trade_date DESC);
    46|CREATE INDEX idx_klines_date ON daily_klines(trade_date DESC);
    47|COMMENT ON TABLE daily_klines IS '日K线数据+技术指标，预计600万行/年，按年分区';
    48|COMMENT ON COLUMN daily_klines.adjust_flag IS '复权标志：none=不复权, front=前复权, back=后复权';
    49|
    50|CREATE TABLE fund_flows (
    51|    id              BIGSERIAL       PRIMARY KEY,
    52|    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    53|    trade_date      DATE            NOT NULL,
    54|    net_amount      NUMERIC(18,4),                      -- 净流入额
    55|    main_amount     NUMERIC(18,4),                      -- 主力净流入
    56|    large_order_pct NUMERIC(8,4),                       -- 大单占比
    57|    small_order_pct NUMERIC(8,4),                       -- 小单占比
    58|    cmf             NUMERIC(10,6),                       -- CMF指标
    59|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    60|    UNIQUE(stock_code, trade_date)
    61|);
    62|CREATE INDEX idx_fund_code_date ON fund_flows(stock_code, trade_date DESC);
    63|COMMENT ON TABLE fund_flows IS '资金流向数据（AKShare），用于策略一筛选';
    64|
    65|CREATE TABLE news (
    66|    id              BIGSERIAL       PRIMARY KEY,
    67|    source          VARCHAR(30)     NOT NULL,           -- cls/wallstcn/gelonghui/jin10/xueqiu/akshare
    68|    source_display  VARCHAR(30)     NOT NULL,           -- 财联社/华尔街见闻/格隆汇/金十数据/雪球/AKShare
    69|    category        VARCHAR(20)     NOT NULL DEFAULT 'finance',  -- finance/stock/macro
    70|    title           VARCHAR(500)    NOT NULL,
    71|    content         TEXT,                               -- 正文/摘要
    72|    url             VARCHAR(500),                       -- 原文链接
    73|    published_at    TIMESTAMPTZ     NOT NULL,
    74|    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    75|    tags            JSONB           DEFAULT '[]',       -- 分类标签: ["policy","earnings"]
    76|    related_stocks  JSONB           DEFAULT '[]',       -- 关联股票代码: ["600519.SH","000858.SZ"]
    77|    sentiment       VARCHAR(10),                        -- positive/neutral/negative
    78|    is_hot          BOOLEAN         DEFAULT FALSE,       -- 是否热点
    79|    hot_score       INTEGER         DEFAULT 0,           -- 热度分（源提供或计算得出）
    80|    extra           JSONB           DEFAULT '{}',        -- 源特有字段（如雪球的percent、金十的important）
    81|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    82|    UNIQUE(url)
    83|);
    84|CREATE INDEX idx_news_published ON news(published_at DESC);
    85|CREATE INDEX idx_news_source ON news(source);
    86|CREATE INDEX idx_news_category ON news(category);
    87|CREATE INDEX idx_news_related ON news USING GIN(related_stocks);
    88|CREATE INDEX idx_news_tags ON news USING GIN(tags);
    89|CREATE INDEX idx_news_hot ON news(is_hot, hot_score DESC) WHERE is_hot = TRUE;
    90|COMMENT ON TABLE news IS '财经新闻数据，复用StockAgent多源采集架构，支持5+1源并发采集';
    91|COMMENT ON COLUMN news.source IS '新闻源标识: cls=财联社, wallstcn=华尔街见闻, gelonghui=格隆汇, jin10=金十, xueqiu=雪球, akshare=AKShare个股新闻';
    92|COMMENT ON COLUMN news.extra IS '各源特有数据，如雪球的{percent:"+2.35%",exchange:"SZ"}, 金十的{important:true,desc:"..."}';
    93|
    94|CREATE TABLE sector_data (
    95|    id              BIGSERIAL       PRIMARY KEY,
    96|    sector_code     VARCHAR(20)     NOT NULL,           -- 板块代码
    97|    sector_name     VARCHAR(50)     NOT NULL,           -- 板块名称
    98|    sector_type     VARCHAR(20)     NOT NULL,           -- industry/concept/area
    99|    trade_date      DATE            NOT NULL,
   100|    capital_ratio   NUMERIC(8,4),                       -- 资金净流入占比
   101|    turnover_rate   NUMERIC(8,4),                       -- 板块换手率
   102|    top_volume_stock VARCHAR(10),                       -- 成交额最大股票
   103|    leader_stocks   JSONB           DEFAULT '[]',       -- 龙头股列表
   104|    change_pct      NUMERIC(8,4),                       -- 涨跌幅
   105|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   106|    UNIQUE(sector_code, trade_date)
   107|);
   108|CREATE INDEX idx_sector_type_date ON sector_data(sector_type, trade_date DESC);
   109|CREATE INDEX idx_sector_code ON sector_data(sector_code);
   110|COMMENT ON TABLE sector_data IS '板块数据（行业/概念/地域），每日更新';
   111|
   112|CREATE TABLE macroeconomic (
   113|    id              BIGSERIAL       PRIMARY KEY,
   114|    indicator_type  VARCHAR(50)     NOT NULL,           -- cpi/ppi/pmi/gdp/...
   115|    indicator_name  VARCHAR(100)    NOT NULL,           -- 指标中文名
   116|    value           NUMERIC(18,4),                      -- 指标值
   117|    period          VARCHAR(20)     NOT NULL,           -- 2026-03/2026-Q1/2026
   118|    published_at    TIMESTAMPTZ,                        -- 发布时间
   119|    source          VARCHAR(30)     NOT NULL DEFAULT 'akshare',
   120|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   121|    UNIQUE(indicator_type, period)
   122|);
   123|CREATE INDEX idx_macro_type ON macroeconomic(indicator_type);
   124|COMMENT ON TABLE macroeconomic IS '宏观经济指标，辅助市场状态判断';
   125|
   126|CREATE TABLE data_sync_log (
   127|    id              BIGSERIAL       PRIMARY KEY,
   128|    task_name       VARCHAR(100)    NOT NULL,           -- 同步任务名
   129|    data_source     VARCHAR(30)     NOT NULL,           -- akshare/miniqmt/wallstcn
   130|    status          VARCHAR(20)     NOT NULL,           -- running/success/failed
   131|    records_affected INTEGER        DEFAULT 0,          -- 影响行数
   132|    error_message   TEXT,                               -- 失败原因
   133|    started_at      TIMESTAMPTZ     NOT NULL,
   134|    finished_at     TIMESTAMPTZ,
   135|    duration_ms     INTEGER                             -- 耗时毫秒
   136|);
   137|CREATE INDEX idx_sync_task ON data_sync_log(task_name, started_at DESC);
   138|CREATE INDEX idx_sync_status ON data_sync_log(status) WHERE status = 'failed';
   139|COMMENT ON TABLE data_sync_log IS '数据同步任务日志，用于质量监控';
   140|
   141|CREATE TABLE market_state_log (
   142|    id              SERIAL          PRIMARY KEY,
   143|    date            DATE            NOT NULL,
   144|    from_state      VARCHAR(16)     NOT NULL,   -- 底部机会期/主线确认/趋势上升期/非主线状态/观望态
   145|    to_state        VARCHAR(16)     NOT NULL,
   146|    trigger_reason  TEXT            NOT NULL,    -- 触发原因描述
   147|    main_line_sector VARCHAR(32),               -- 当前主线板块
   148|    confidence      NUMERIC(4,2),               -- 状态切换信心分
   149|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   150|);
   151|CREATE INDEX idx_market_state_date ON market_state_log(date DESC);
   152|COMMENT ON TABLE market_state_log IS '市场状态转换日志，每次状态切换必须记录';
   153|
   154|CREATE TABLE stock_pool (
   155|    id              BIGSERIAL       PRIMARY KEY,
   156|    date            DATE            NOT NULL,
   157|    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   158|    strategy_type   VARCHAR(20)     NOT NULL,    -- bottom_volume / trend_momentum
   159|    pass_coarse     BOOLEAN         NOT NULL DEFAULT FALSE,
   160|    score_total     NUMERIC(6,2),               -- 总评分
   161|    score_volume    NUMERIC(6,2),               -- 量价维度分
   162|    score_fund      NUMERIC(6,2),               -- 资金维度分
   163|    score_sentiment NUMERIC(6,2),               -- 情绪维度分
   164|    score_mainforce NUMERIC(6,2),               -- 主力行为维度分
   165|    score_logic     NUMERIC(6,2),               -- 资本市场逻辑维度分
   166|    agent_scores    JSONB           DEFAULT '{}',
   167|    final_decision  VARCHAR(10),                -- buy / hold / reject
   168|    final_score     NUMERIC(6,2),               -- 加权投票后总分
   169|    position_pct    NUMERIC(4,2),               -- 建议仓位比例
   170|    stop_loss_pct   NUMERIC(4,2),               -- 止损百分比
   171|    stop_profit_pct NUMERIC(4,2),               -- 止盈百分比
   172|    reject_reason   TEXT,                       -- 拒绝原因
   173|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   174|    UNIQUE(date, stock_code, strategy_type)
   175|);
   176|CREATE INDEX idx_pool_date ON stock_pool(date DESC);
   177|CREATE INDEX idx_pool_decision ON stock_pool(date, final_decision);
   178|CREATE INDEX idx_pool_strategy ON stock_pool(strategy_type, date DESC);
   179|COMMENT ON TABLE stock_pool IS '每日股票池，记录筛选全流程结果';
   180|
   181|CREATE TABLE strategy_params (
   182|    id              SERIAL          PRIMARY KEY,
   183|    strategy_type   VARCHAR(20)     NOT NULL,    -- bottom_volume / trend_momentum / common
   184|    param_key       VARCHAR(50)     NOT NULL,
   185|    param_value     TEXT            NOT NULL,
   186|    param_type      VARCHAR(20)     NOT NULL DEFAULT 'string',
   187|    description     TEXT,
   188|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   189|    UNIQUE(strategy_type, param_key)
   190|);
   191|INSERT INTO strategy_params (strategy_type, param_key, param_value, param_type, description) VALUES
   192|('bottom_volume', 'decline_60d_pct', '20', 'int', '近60日跌幅阈值(%)'),
   193|('bottom_volume', 'sharp_drop_5d_pct', '5', 'int', '近5日单日跌幅阈值(%)'),
   194|('bottom_volume', 'market_cap_min', '50', 'int', '最小市值(亿)'),
   195|('bottom_volume', 'market_cap_max', '500', 'int', '最大市值(亿)'),
   196|('bottom_volume', 'min_daily_amount', '1', 'int', '日均成交额最小值(亿)'),
   197|('bottom_volume', 'min_list_days', '180', 'int', '最少上市天数'),
   198|('trend_momentum', 'sector_capital_ratio', '12', 'int', '板块资金集中度阈值(%)'),
   199|('trend_momentum', 'sector_hot_days', '2', 'int', '板块连续热门天数'),
   200|('trend_momentum', 'adx_threshold', '25', 'int', 'ADX趋势强度阈值'),
   201|('trend_momentum', 'volume_shrink_pct', '80', 'int', '缩量回踩阈值(%)'),
   202|('trend_momentum', 'drop_3d_pct', '3', 'int', '3日回踩跌幅阈值(%)'),
   203|('trend_momentum', 'min_daily_amount', '3', 'int', '日均成交额最小值(亿)'),
   204|('common', 'state_cooldown_days', '3', 'int', '状态切换冷却期(天)'),
   205|('common', 'max_main_lines', '2', 'int', '最大主线并行数'),
   206|('common', 'oscillation_threshold', '3', 'int', '震荡保护来回切换次数'),
   207|('common', 'max_position_per_stock', '30', 'int', '单票最大仓位(%)'),
   208|('common', 'premarket_gap_pct', '3', 'int', '开盘前复核跳空阈值(%)');
   209|
   210|CREATE TABLE backtest_results (
   211|    id              BIGSERIAL       PRIMARY KEY,
   212|    strategy_type   VARCHAR(20)     NOT NULL,
   213|    start_date      DATE            NOT NULL,
   214|    end_date        DATE            NOT NULL,
   215|    initial_capital NUMERIC(18,2)   NOT NULL,
   216|    final_capital   NUMERIC(18,2)   NOT NULL,
   217|    annual_return   NUMERIC(8,4),               -- 年化收益率
   218|    max_drawdown    NUMERIC(8,4),               -- 最大回撤
   219|    win_rate        NUMERIC(8,4),               -- 胜率
   220|    profit_loss_ratio NUMERIC(8,4),             -- 盈亏比
   221|    total_trades    INTEGER,                    -- 总交易次数
   222|    params_used     JSONB           NOT NULL,    -- 使用的策略参数快照
   223|    daily_equity    JSONB,                      -- 每日净值曲线
   224|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   225|);
   226|CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_type, start_date DESC);
   227|
   228|CREATE TABLE agent_discussions (
   229|    id              BIGSERIAL       PRIMARY KEY,
   230|    date            DATE            NOT NULL,                       -- 讨论日期
   231|    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code), -- 标的
   232|    round_num       SMALLINT        NOT NULL DEFAULT 1,             -- 讨论轮次(1-3)
   233|    agent_name      VARCHAR(32)     NOT NULL,                       -- Agent名称
   234|    score           SMALLINT,                                       -- Agent评分 0-100
   235|    buy_reasons     JSONB           NOT NULL DEFAULT '[]',          -- 买入理由数组
   236|    against_reasons JSONB           NOT NULL DEFAULT '[]',          -- 反对理由数组 [PRD-T-102]
   237|    confidence      NUMERIC(4,2)    DEFAULT 0.5,                    -- 信心度 0-1
   238|    prompt_tokens   INTEGER         DEFAULT 0,                      -- [PRD-T-112]
   239|    completion_tokens INTEGER       DEFAULT 0,                      -- [PRD-T-112]
   240|    model_name      VARCHAR(32),                                    -- 使用的LLM模型
   241|    is_valid        BOOLEAN         NOT NULL DEFAULT TRUE,          -- 校验后是否有效
   242|    invalid_reason  VARCHAR(64),                                    -- 无效原因
   243|    predicted_outcome VARCHAR(16),                                  -- buy/hold/avoid
   244|    actual_outcome  VARCHAR(16),                                    -- win/loss/pending
   245|    outcome_updated_at TIMESTAMPTZ,                                 -- 实际结果更新时间
   246|    raw_response    TEXT,                                           -- LLM原始响应(调试用)
   247|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   248|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   249|);
   250|CREATE INDEX idx_agent_disc_date_stock ON agent_discussions(date DESC, stock_code);
   251|CREATE INDEX idx_agent_disc_agent ON agent_discussions(agent_name, date DESC);
   252|CREATE INDEX idx_agent_disc_outcome ON agent_discussions(predicted_outcome, actual_outcome)
   253|    WHERE predicted_outcome IS NOT NULL;
   254|COMMENT ON TABLE agent_discussions IS 'Agent讨论记录，每位Agent对每只股票每轮的完整输出';
   255|
   256|CREATE TABLE agent_weights (
   257|    id              BIGSERIAL       PRIMARY KEY,
   258|    agent_name      VARCHAR(32)     NOT NULL,               -- Agent名称
   259|    market_state    VARCHAR(16)     NOT NULL,               -- 适用市场状态
   260|    base_weight     NUMERIC(4,2)    NOT NULL,               -- 基准权重(市场状态决定)
   261|    calib_factor    NUMERIC(4,2)    NOT NULL DEFAULT 1.0,   -- 校准系数 [PRD-T-106] 上限1.3/下限0.3
   262|    effective_weight NUMERIC(4,2)   NOT NULL,               -- 有效权重 = base_weight × calib_factor
   263|    win_rate        NUMERIC(5,4)    DEFAULT 0.5,            -- 最近20次滚动胜率
   264|    recent_count    INTEGER         DEFAULT 0,              -- 统计样本数
   265|    extreme_count   INTEGER         DEFAULT 0,              -- 连续极端评分次数
   266|    is_degraded     BOOLEAN         DEFAULT FALSE,          -- 是否已被降权
   267|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   268|    CONSTRAINT uk_agent_weight UNIQUE (agent_name, market_state),
   269|    CONSTRAINT chk_calib_factor CHECK (calib_factor >= 0.3 AND calib_factor <= 1.3),  -- PRD L938 强约束
   270|    CONSTRAINT chk_base_weight CHECK (base_weight > 0 AND base_weight <= 1.0)
   271|);
   272|INSERT INTO agent_weights (agent_name, market_state, base_weight, calib_factor, effective_weight) VALUES
   273|('mainline_hunter',  'mainline_confirmed', 0.35, 1.0, 0.35),
   274|('fund_detective',   'mainline_confirmed', 0.25, 1.0, 0.25),
   275|('sentiment_catcher','mainline_confirmed', 0.15, 1.0, 0.15),
   276|('experience_judge', 'mainline_confirmed', 0.25, 1.0, 0.25);
   277|INSERT INTO agent_weights (agent_name, market_state, base_weight, calib_factor, effective_weight) VALUES
   278|('mainline_hunter',  'oscillating', 0.20, 1.0, 0.20),
   279|('fund_detective',   'oscillating', 0.25, 1.0, 0.25),
   280|('sentiment_catcher','oscillating', 0.20, 1.0, 0.20),
   281|('experience_judge', 'oscillating', 0.35, 1.0, 0.35);
   282|COMMENT ON TABLE agent_weights IS 'Agent权重配置与校准，按市场状态分组，含滚动胜率追踪';
   283|
   284|CREATE TABLE agent_decisions (
   285|    id              BIGSERIAL       PRIMARY KEY,
   286|    date            DATE            NOT NULL,
   287|    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   288|    total_score     NUMERIC(6,2),                           -- 加权总分
   289|    buy_score_sum   NUMERIC(6,2),                           -- 买入理由加权总分 [PRD-T-103]
   290|    against_score_sum NUMERIC(6,2),                         -- 反对理由加权总分
   291|    net_score       NUMERIC(6,2),                           -- buy_score_sum - against_score_sum
   292|    decision        VARCHAR(16)    NOT NULL,                 -- buy/hold/reject
   293|    decision_reason TEXT,                                    -- 决策原因
   294|    agent_votes_json JSONB        NOT NULL DEFAULT '{}',     -- {agent_name: {score, weight, effective_score}}
   295|    risk_veto       BOOLEAN       DEFAULT FALSE,             -- 风控一票否决 [PRD-T-101]
   296|    risk_veto_reason VARCHAR(128),                           -- 否决原因
   297|    convergence_rounds SMALLINT   DEFAULT 0,                 -- 实际收敛轮次
   298|    convergence_method VARCHAR(32),                          -- normal/trimmed_mean/degraded
   299|    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
   300|    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
   301|    CONSTRAINT uk_decision UNIQUE (date, stock_code)
   302|);
   303|CREATE INDEX idx_agent_dec_date ON agent_decisions(date DESC);
   304|COMMENT ON TABLE agent_decisions IS '最终加权投票决策，每日每只标的一条，含风控否决标记';
   305|
   306|CREATE TABLE llm_usage (
   307|    id                SERIAL        PRIMARY KEY,
   308|    date              DATE          NOT NULL,
   309|    model             VARCHAR(32)   NOT NULL,                -- LLM模型名
   310|    agent_name        VARCHAR(32),                            -- Agent名称(可为空表示非Agent调用)
   311|    prompt_tokens     INTEGER       DEFAULT 0,               -- [PRD-T-112]
   312|    completion_tokens INTEGER       DEFAULT 0,               -- [PRD-T-112]
   313|    total_cost        DECIMAL(10,4) DEFAULT 0,               -- 估算成本(元)
   314|    call_count        INTEGER       DEFAULT 1,               -- 调用次数
   315|    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
   316|    CONSTRAINT uk_llm_usage UNIQUE (date, model, agent_name)
   317|);
   318|CREATE INDEX idx_llm_usage_date ON llm_usage(date DESC);
   319|CREATE INDEX idx_llm_usage_model ON llm_usage(model, date DESC);
   320|COMMENT ON TABLE llm_usage IS 'LLM Token用量监控，每日每模型每Agent汇总一条';
   321|
   322|CREATE TABLE agent_prompts (
   323|    id              BIGSERIAL       PRIMARY KEY,
   324|    agent_name      VARCHAR(32)     NOT NULL,
   325|    version         VARCHAR(16)     NOT NULL,                -- V1/V2/V3/V4
   326|    system_prompt   TEXT            NOT NULL,                -- 系统提示词
   327|    user_prompt_template TEXT       NOT NULL,                -- 用户提示词模板({{占位符}})
   328|    is_active       BOOLEAN         NOT NULL DEFAULT FALSE,  -- 当前激活版本
   329|    change_note     TEXT,                                    -- 变更说明
   330|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   331|    CONSTRAINT uk_agent_prompt_version UNIQUE (agent_name, version)
   332|);
   333|CREATE INDEX idx_agent_prompts_active ON agent_prompts(agent_name) WHERE is_active = TRUE;
   334|COMMENT ON TABLE agent_prompts IS 'Agent提示词版本管理，支持迭代式开发(V1→V4)';
   335|
   336|CREATE TABLE trade_orders (
   337|    id                BIGSERIAL       PRIMARY KEY,
   338|    client_order_id   VARCHAR(64)     NOT NULL,     -- 幂等键，UUID v4
   339|    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   340|    direction         VARCHAR(10)     NOT NULL,     -- buy / sell
   341|    order_type        VARCHAR(20)     NOT NULL,     -- market / limit
   342|    price             NUMERIC(18,4),                -- 限价单价格，市价单为NULL
   343|    volume            INTEGER         NOT NULL,     -- 委托数量（股）
   344|    filled_volume     INTEGER         NOT NULL DEFAULT 0,
   345|    filled_amount     NUMERIC(18,4)   NOT NULL DEFAULT 0,
   346|    status            VARCHAR(20)     NOT NULL DEFAULT 'pending',
   347|    retry_count       INTEGER         NOT NULL DEFAULT 0,
   348|    max_retry         INTEGER         NOT NULL DEFAULT 3,    -- PRD L613 强约束
   349|    position_batch    VARCHAR(20),                  -- first_half / second_batch / remainder
   350|    trigger_source    VARCHAR(20)     NOT NULL,     -- strategy / stop_loss / stop_profit / manual
   351|    trade_mode        VARCHAR(20)     NOT NULL,     -- SIMULATION / PAPER / LIVE
   352|    broker_order_id   VARCHAR(64),                  -- miniQMT返回的委托编号
   353|    strategy_type     VARCHAR(20),                  -- bottom_volume / trend_momentum
   354|    reason            TEXT,                         -- 交易原因描述
   355|    agent_scores_json JSONB           DEFAULT '{}', -- Agent评分快照
   356|    stop_loss_price   NUMERIC(18,4),               -- 下单时绑定的止损价
   357|    stop_profit_pct   NUMERIC(8,4),                -- 下单时绑定的止盈比例
   358|    error_message     TEXT,                         -- 失败原因
   359|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   360|    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   361|    UNIQUE(client_order_id)
   362|);
   363|CREATE INDEX idx_orders_stock ON trade_orders(stock_code, created_at DESC);
   364|CREATE INDEX idx_orders_status ON trade_orders(status, created_at DESC);
   365|CREATE INDEX idx_orders_date ON trade_orders(created_at DESC);
   366|CREATE INDEX idx_orders_broker ON trade_orders(broker_order_id) WHERE broker_order_id IS NOT NULL;
   367|COMMENT ON TABLE trade_orders IS '交易订单，全链路记录每笔交易';
   368|
   369|CREATE TABLE positions (
   370|    id                BIGSERIAL       PRIMARY KEY,
   371|    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   372|    direction         VARCHAR(10)     NOT NULL DEFAULT 'long',   -- long（A股仅做多）
   373|    total_volume      INTEGER         NOT NULL DEFAULT 0,        -- 总持仓数量
   374|    available_volume  INTEGER         NOT NULL DEFAULT 0,        -- 可卖数量（T+1限制）
   375|    cost_price        NUMERIC(18,4)   NOT NULL DEFAULT 0,        -- 持仓成本价
   376|    market_value      NUMERIC(18,4)   NOT NULL DEFAULT 0,        -- 当前市值
   377|    unrealized_pnl    NUMERIC(18,4)   NOT NULL DEFAULT 0,        -- 浮动盈亏
   378|    unrealized_pnl_pct NUMERIC(8,4)   NOT NULL DEFAULT 0,        -- 浮动盈亏比例
   379|    position_pct      NUMERIC(8,4)   NOT NULL DEFAULT 0,        -- 占总资金比例
   380|    batch_stage       VARCHAR(20)     NOT NULL DEFAULT 'none',   -- none / first_half / second_batch / full
   381|    first_batch_vol   INTEGER         NOT NULL DEFAULT 0,        -- 第一批50%仓位
   382|    second_batch_vol  INTEGER         NOT NULL DEFAULT 0,        -- 第二批5%仓位
   383|    remainder_vol     INTEGER         NOT NULL DEFAULT 0,        -- 剩余仓位
   384|    entry_date        DATE,                                      -- 首次入场日期
   385|    last_trade_at     TIMESTAMPTZ,                               -- 最近交易时间
   386|    is_cooling_down   BOOLEAN         NOT NULL DEFAULT FALSE,    -- 止损/止盈冷却期
   387|    cool_down_until   TIMESTAMPTZ,                               -- 冷却期结束时间
   388|    cool_down_reason  VARCHAR(20),                               -- stop_loss / stop_profit
   389|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   390|    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   391|    UNIQUE(stock_code) WHERE total_volume > 0  -- 活跃持仓唯一
   392|);
   393|CREATE INDEX idx_positions_stock ON positions(stock_code);
   394|CREATE INDEX idx_positions_active ON positions(id) WHERE total_volume > 0;
   395|CREATE INDEX idx_positions_cooling ON positions(stock_code) WHERE is_cooling_down = TRUE;
   396|COMMENT ON TABLE positions IS '持仓管理，推进式仓位分批建仓';
   397|
   398|CREATE TABLE stop_loss_conditions (
   399|    id                BIGSERIAL       PRIMARY KEY,
   400|    position_id       BIGINT          NOT NULL REFERENCES positions(id),
   401|    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   402|    condition_type    VARCHAR(20)     NOT NULL,     -- fixed_price / trailing / max_loss
   403|    stop_loss_price   NUMERIC(18,4)   NOT NULL,     -- 止损价格
   404|    trigger_price     NUMERIC(18,4),                -- 触发价（跟踪止损用）
   405|    trailing_pct      NUMERIC(8,4),                 -- 跟踪止损回撤比例
   406|    max_loss_amount   NUMERIC(18,4),                -- 最大亏损金额（=总资金×1.5%）
   407|    max_loss_pct      NUMERIC(8,4)    NOT NULL,     -- 最大亏损比例
   408|    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
   409|    triggered_at      TIMESTAMPTZ,                  -- 触发时间
   410|    trigger_price_actual NUMERIC(18,4),             -- 实际触发时价格
   411|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   412|    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   413|);
   414|CREATE INDEX idx_stoploss_position ON stop_loss_conditions(position_id);
   415|CREATE INDEX idx_stoploss_stock ON stop_loss_conditions(stock_code, is_active);
   416|CREATE INDEX idx_stoploss_active ON stop_loss_conditions(id) WHERE is_active = TRUE;
   417|COMMENT ON TABLE stop_loss_conditions IS '止损条件，下单前提绑定，独立进程检查';
   418|
   419|CREATE TABLE trade_mode (
   420|    id                SERIAL          PRIMARY KEY,
   421|    current_mode      VARCHAR(20)     NOT NULL DEFAULT 'SIMULATION',  -- SIMULATION/PAPER/LIVE
   422|    confirm_mode      VARCHAR(20)     NOT NULL DEFAULT 'advisory',    -- advisory/semi_auto/full_auto
   423|    mode_password_hash VARCHAR(255),                                  -- 模式切换密码(bcrypt)
   424|    upgraded_at       TIMESTAMPTZ,                                   -- 最近升级时间
   425|    emergency_stop    BOOLEAN         NOT NULL DEFAULT FALSE,         -- 紧急停止标志
   426|    emergency_stopped_at TIMESTAMPTZ,                                -- 紧急停止时间
   427|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   428|    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   429|);
   430|INSERT INTO trade_mode (current_mode, confirm_mode) VALUES ('SIMULATION', 'advisory');
   431|COMMENT ON TABLE trade_mode IS '交易模式配置，三态+单向升级';
   432|
   433|CREATE TABLE stop_profit_conditions (
   434|    id                BIGSERIAL       PRIMARY KEY,
   435|    position_id       BIGINT          NOT NULL REFERENCES positions(id),
   436|    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
   437|    stage             VARCHAR(20)     NOT NULL,     -- first_take / second_take / trailing
   438|    trigger_pct       NUMERIC(8,4)    NOT NULL,     -- 触发涨幅百分比
   439|    sell_pct          NUMERIC(8,4)    NOT NULL,     -- 卖出仓位比例
   440|    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
   441|    triggered_at      TIMESTAMPTZ,
   442|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   443|    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   444|);
   445|CREATE INDEX idx_stopprofit_position ON stop_profit_conditions(position_id);
   446|CREATE INDEX idx_stopprofit_active ON stop_profit_conditions(id) WHERE is_active = TRUE;
   447|COMMENT ON TABLE stop_profit_conditions IS '阶梯止盈条件，硬约束触发即执行';
   448|
   449|CREATE TABLE account_sync_log (
   450|    id                BIGSERIAL       PRIMARY KEY,
   451|    sync_type         VARCHAR(20)     NOT NULL,     -- total_asset / positions / daily_pnl / history_trades
   452|    total_asset       NUMERIC(18,4),                -- 总资产
   453|    available_cash    NUMERIC(18,4),                -- 可用资金
   454|    frozen_cash       NUMERIC(18,4),                -- 冻结资金
   455|    daily_pnl         NUMERIC(18,4),                -- 当日盈亏
   456|    positions_json    JSONB,                        -- 持仓快照
   457|    sync_status       VARCHAR(10)     NOT NULL DEFAULT 'success',  -- success / failed
   458|    error_message     TEXT,
   459|    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   460|);
   461|CREATE INDEX idx_account_sync_type ON account_sync_log(sync_type, created_at DESC);
   462|COMMENT ON TABLE account_sync_log IS '账户资产同步记录';
   463|
   464|CREATE TABLE risk_events (
   465|    id              BIGSERIAL       PRIMARY KEY,
   466|    event_type      VARCHAR(40)     NOT NULL,    -- 事件类型，见 2.2 枚举
   467|    event_level     VARCHAR(20)     NOT NULL,    -- critical/warning/info
   468|    trigger_value   NUMERIC(18,4),               -- 触发值
   469|    threshold_value NUMERIC(18,4),               -- 阈值
   470|    trigger_reason  TEXT            NOT NULL,    -- 触发原因描述
   471|    action_taken    VARCHAR(40)     NOT NULL,    -- 执行的处置动作
   472|    action_detail   JSONB           DEFAULT '{}', -- 处置详情
   473|    recovery_path   VARCHAR(10),                -- 复苏路径 A/B/C（仅暂停/全停事件）
   474|    recovery_status VARCHAR(20)     DEFAULT 'pending', -- pending/recovering/resolved
   475|    recovery_deadline DATE,                     -- 复苏截止日期
   476|    resolved_at     TIMESTAMPTZ,                 -- 解除时间
   477|    trade_date      DATE            NOT NULL,    -- 交易日期
   478|    is_intraday     BOOLEAN         NOT NULL DEFAULT FALSE, -- 是否盘中触发
   479|    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
   480|    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
   481|);
   482|CREATE INDEX idx_risk_events_date ON risk_events(trade_date DESC);
   483|CREATE INDEX idx_risk_events_type ON risk_events(event_type, trade_date DESC);
   484|CREATE INDEX idx_risk_events_level ON risk_events(event_level, trade_date DESC);
   485|CREATE INDEX idx_risk_events_recovery ON risk_events(recovery_status, recovery_path)
   486|    WHERE recovery_status != 'resolved';
   487|COMMENT ON TABLE risk_events IS '风控事件记录，每次风控触发必须写入';
   488|
   489|CREATE TABLE risk_metrics_daily (
   490|    id              BIGSERIAL       PRIMARY KEY,
   491|    trade_date      DATE            NOT NULL,
   492|    daily_drawdown  NUMERIC(8,4),               -- 单日回撤率
   493|    max_drawdown    NUMERIC(8,4),               -- 历史最大回撤
   494|    win_rate        NUMERIC(8,4),               -- 当日胜率
   495|    win_rate_3d     NUMERIC(8,4),               -- 近3日滚动胜率
   496|    consecutive_loss_days INTEGER   DEFAULT 0,  -- 连续亏损天数
   497|    profit_loss_ratio NUMERIC(8,4),             -- 当日盈亏比
   498|    pl_ratio_rolling NUMERIC(8,4),              -- 滚动盈亏比（近20笔）
   499|    consecutive_losses INTEGER    DEFAULT 0,    -- 连续亏损次数
   500|    total_position_pct NUMERIC(8,4),            -- 总仓位占比
   501|


-- ===== 以下为补充表（DD提取时因条件索引语法跳过） =====

CREATE TABLE IF NOT EXISTS positions (
    id                BIGSERIAL       PRIMARY KEY,
    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    direction         VARCHAR(10)     NOT NULL DEFAULT 'long',
    total_volume      INTEGER         NOT NULL DEFAULT 0,
    available_volume  INTEGER         NOT NULL DEFAULT 0,
    cost_price        NUMERIC(18,4)   NOT NULL DEFAULT 0,
    market_value      NUMERIC(18,4)   NOT NULL DEFAULT 0,
    unrealized_pnl    NUMERIC(18,4)   NOT NULL DEFAULT 0,
    unrealized_pnl_pct NUMERIC(8,4)   NOT NULL DEFAULT 0,
    position_pct      NUMERIC(8,4)   NOT NULL DEFAULT 0,
    batch_stage       VARCHAR(20)     NOT NULL DEFAULT 'none',
    first_batch_vol   INTEGER         NOT NULL DEFAULT 0,
    second_batch_vol  INTEGER         NOT NULL DEFAULT 0,
    remainder_vol     INTEGER         NOT NULL DEFAULT 0,
    entry_date        DATE,
    last_trade_at     TIMESTAMPTZ,
    is_cooling_down   BOOLEAN         NOT NULL DEFAULT FALSE,
    cool_down_until   TIMESTAMPTZ,
    cool_down_reason  VARCHAR(20),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_positions_stock ON positions(stock_code);
CREATE INDEX IF NOT EXISTS idx_positions_cooling ON positions(stock_code) WHERE is_cooling_down = TRUE;
COMMENT ON TABLE positions IS '持仓管理，推进式仓位分批建仓';

CREATE TABLE IF NOT EXISTS stop_loss_conditions (
    id                BIGSERIAL       PRIMARY KEY,
    position_id       BIGINT          NOT NULL REFERENCES positions(id),
    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    condition_type    VARCHAR(20)     NOT NULL,
    stop_loss_price   NUMERIC(18,4)   NOT NULL,
    trigger_price     NUMERIC(18,4),
    trailing_pct      NUMERIC(8,4),
    max_loss_amount   NUMERIC(18,4),
    max_loss_pct      NUMERIC(8,4)    NOT NULL,
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    triggered_at      TIMESTAMPTZ,
    trigger_price_actual NUMERIC(18,4),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stoploss_position ON stop_loss_conditions(position_id);
CREATE INDEX IF NOT EXISTS idx_stoploss_stock ON stop_loss_conditions(stock_code, is_active);
CREATE INDEX IF NOT EXISTS idx_stoploss_active ON stop_loss_conditions(id) WHERE is_active = TRUE;
COMMENT ON TABLE stop_loss_conditions IS '止损条件，下单前提绑定，独立进程检查';

INSERT INTO trade_mode (current_mode, confirm_mode) VALUES ('SIMULATION', 'advisory');

CREATE TABLE IF NOT EXISTS stop_profit_conditions (
    id                BIGSERIAL       PRIMARY KEY,
    position_id       BIGINT          NOT NULL REFERENCES positions(id),
    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    stage             VARCHAR(20)     NOT NULL,
    trigger_pct       NUMERIC(8,4)    NOT NULL,
    sell_pct          NUMERIC(8,4)    NOT NULL,
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    triggered_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE stop_profit_conditions IS '止盈条件，阶梯止盈';

