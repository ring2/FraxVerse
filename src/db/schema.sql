# =============================================================================
# FraxVerse · 碎片宇宙智能量化交易系统
# SQL 初始化脚本 — 聚合所有DD文档的CREATE TABLE语句
# 来源：DD-01 ~ DD-09
# =============================================================================

-- ============================================================================
-- DD-01: 认证与用户模块
-- ============================================================================

CREATE TABLE users (
    id              SERIAL          PRIMARY KEY,
    username        VARCHAR(20)     NOT NULL UNIQUE,
                    CONSTRAINT uk_users_username UNIQUE (username),
    password_hash   VARCHAR(128)    NOT NULL,           -- bcrypt hash, cost=12
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ,                        -- 最后登录时间
    login_count     INTEGER         NOT NULL DEFAULT 0,  -- 累计登录次数
    is_initialized  BOOLEAN         NOT NULL DEFAULT TRUE -- 初始化完成后标记
);
COMMENT ON TABLE users IS '用户表（单用户系统，仅1行记录）';
COMMENT ON COLUMN users.password_hash IS 'bcrypt加密密码，cost factor=12';
COMMENT ON COLUMN users.is_initialized IS 'TRUE表示系统已完成首次设置';

CREATE TABLE sessions (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_jti      VARCHAR(36)     NOT NULL UNIQUE,
    refresh_jti     VARCHAR(36)     NOT NULL UNIQUE,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    access_expires  TIMESTAMPTZ     NOT NULL,
    refresh_expires TIMESTAMPTZ     NOT NULL,
    revoked         BOOLEAN         NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_sessions_access_jti ON sessions(access_jti);
CREATE INDEX idx_sessions_refresh_jti ON sessions(refresh_jti);
CREATE INDEX idx_sessions_user_active ON sessions(user_id) WHERE revoked = FALSE;
COMMENT ON TABLE sessions IS '会话记录表，用于Token黑名单和活跃会话管理';

CREATE TABLE system_config (
    id              SERIAL          PRIMARY KEY,
    config_key      VARCHAR(100)    NOT NULL UNIQUE,
    config_value    TEXT            NOT NULL,
    config_type     VARCHAR(20)     NOT NULL DEFAULT 'string',
    description     TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- DD-02: 数据管理模块
-- ============================================================================

CREATE TABLE stocks (
    code            VARCHAR(10)     PRIMARY KEY,
    name            VARCHAR(20)     NOT NULL,
    industry        VARCHAR(30),
    market          VARCHAR(10)     NOT NULL,
    list_date       DATE,
    is_st           BOOLEAN         NOT NULL DEFAULT FALSE,
    is_suspended    BOOLEAN         NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_stocks_st ON stocks(is_st) WHERE is_st = TRUE;
CREATE INDEX idx_stocks_suspended ON stocks(is_suspended) WHERE is_suspended = TRUE;
CREATE INDEX idx_stocks_industry ON stocks(industry);
COMMENT ON TABLE stocks IS 'A股基本信息表，约5000行';

CREATE TABLE daily_klines (
    id              BIGSERIAL       PRIMARY KEY,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    trade_date      DATE            NOT NULL,
    open            NUMERIC(10,2)   NOT NULL,
    high            NUMERIC(10,2)   NOT NULL,
    low             NUMERIC(10,2)   NOT NULL,
    close           NUMERIC(10,2)   NOT NULL,
    volume          BIGINT          NOT NULL,
    amount          NUMERIC(18,2)   NOT NULL,
    turnover_rate   NUMERIC(8,4),
    adjust_flag     VARCHAR(10)     NOT NULL DEFAULT 'none',
    ma5             NUMERIC(10,2),
    ma10            NUMERIC(10,2),
    ma20            NUMERIC(10,2),
    ma60            NUMERIC(10,2),
    adx             NUMERIC(8,4),
    cmf             NUMERIC(10,6),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(stock_code, trade_date, adjust_flag)
);
CREATE INDEX idx_klines_code_date ON daily_klines(stock_code, trade_date DESC);
CREATE INDEX idx_klines_date ON daily_klines(trade_date DESC);
COMMENT ON TABLE daily_klines IS '日K线数据+技术指标，预计600万行/年，按年分区';

CREATE TABLE fund_flows (
    id              BIGSERIAL       PRIMARY KEY,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    trade_date      DATE            NOT NULL,
    net_amount      NUMERIC(18,4),
    main_amount     NUMERIC(18,4),
    large_order_pct NUMERIC(8,4),
    small_order_pct NUMERIC(8,4),
    cmf             NUMERIC(10,6),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(stock_code, trade_date)
);
CREATE INDEX idx_fund_code_date ON fund_flows(stock_code, trade_date DESC);
COMMENT ON TABLE fund_flows IS '资金流向数据（AKShare），用于策略一筛选';

CREATE TABLE news (
    id              BIGSERIAL       PRIMARY KEY,
    source          VARCHAR(30)     NOT NULL,
    source_display  VARCHAR(30)     NOT NULL,
    category        VARCHAR(20)     NOT NULL DEFAULT 'finance',
    title           VARCHAR(500)    NOT NULL,
    content         TEXT,
    url             VARCHAR(500),
    published_at    TIMESTAMPTZ     NOT NULL,
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    tags            JSONB           DEFAULT '[]',
    related_stocks  JSONB           DEFAULT '[]',
    sentiment       VARCHAR(10),
    is_hot          BOOLEAN         DEFAULT FALSE,
    hot_score       INTEGER         DEFAULT 0,
    extra           JSONB           DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(url)
);
CREATE INDEX idx_news_published ON news(published_at DESC);
CREATE INDEX idx_news_source ON news(source);
CREATE INDEX idx_news_category ON news(category);
CREATE INDEX idx_news_related ON news USING GIN(related_stocks);
CREATE INDEX idx_news_tags ON news USING GIN(tags);
CREATE INDEX idx_news_hot ON news(is_hot, hot_score DESC) WHERE is_hot = TRUE;
COMMENT ON TABLE news IS '财经新闻数据，复用StockAgent多源采集架构';

CREATE TABLE sector_data (
    id              BIGSERIAL       PRIMARY KEY,
    sector_code     VARCHAR(20)     NOT NULL,
    sector_name     VARCHAR(50)     NOT NULL,
    sector_type     VARCHAR(20)     NOT NULL,
    trade_date      DATE            NOT NULL,
    capital_ratio   NUMERIC(8,4),
    turnover_rate   NUMERIC(8,4),
    top_volume_stock VARCHAR(10),
    leader_stocks   JSONB           DEFAULT '[]',
    change_pct      NUMERIC(8,4),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(sector_code, trade_date)
);
CREATE INDEX idx_sector_type_date ON sector_data(sector_type, trade_date DESC);
CREATE INDEX idx_sector_code ON sector_data(sector_code);
COMMENT ON TABLE sector_data IS '板块数据（行业/概念/地域），每日更新';

CREATE TABLE macroeconomic (
    id              BIGSERIAL       PRIMARY KEY,
    indicator_type  VARCHAR(50)     NOT NULL,
    indicator_name  VARCHAR(100)    NOT NULL,
    value           NUMERIC(18,4),
    period          VARCHAR(20)     NOT NULL,
    published_at    TIMESTAMPTZ,
    source          VARCHAR(30)     NOT NULL DEFAULT 'akshare',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(indicator_type, period)
);
CREATE INDEX idx_macro_type ON macroeconomic(indicator_type);
COMMENT ON TABLE macroeconomic IS '宏观经济指标，辅助市场状态判断';

CREATE TABLE data_sync_log (
    id              BIGSERIAL       PRIMARY KEY,
    task_name       VARCHAR(100)    NOT NULL,
    data_source     VARCHAR(30)     NOT NULL,
    status          VARCHAR(20)     NOT NULL,
    records_affected INTEGER        DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ     NOT NULL,
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER
);
CREATE INDEX idx_sync_task ON data_sync_log(task_name, started_at DESC);
CREATE INDEX idx_sync_status ON data_sync_log(status) WHERE status = 'failed';
COMMENT ON TABLE data_sync_log IS '数据同步任务日志，用于质量监控';

-- ============================================================================
-- DD-03: 策略引擎模块
-- ============================================================================

CREATE TABLE market_state_log (
    id              SERIAL          PRIMARY KEY,
    date            DATE            NOT NULL,
    from_state      VARCHAR(16)     NOT NULL,
    to_state        VARCHAR(16)     NOT NULL,
    trigger_reason  TEXT            NOT NULL,
    main_line_sector VARCHAR(32),
    confidence      NUMERIC(4,2),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_market_state_date ON market_state_log(date DESC);
COMMENT ON TABLE market_state_log IS '市场状态转换日志，每次状态切换必须记录';

CREATE TABLE stock_pool (
    id              BIGSERIAL       PRIMARY KEY,
    date            DATE            NOT NULL,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    strategy_type   VARCHAR(20)     NOT NULL,
    pass_coarse     BOOLEAN         NOT NULL DEFAULT FALSE,
    score_total     NUMERIC(6,2),
    score_volume    NUMERIC(6,2),
    score_fund      NUMERIC(6,2),
    score_sentiment NUMERIC(6,2),
    score_mainforce NUMERIC(6,2),
    score_logic     NUMERIC(6,2),
    agent_scores    JSONB           DEFAULT '{}',
    final_decision  VARCHAR(10),
    final_score     NUMERIC(6,2),
    position_pct    NUMERIC(4,2),
    stop_loss_pct   NUMERIC(4,2),
    stop_profit_pct NUMERIC(4,2),
    reject_reason   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(date, stock_code, strategy_type)
);
CREATE INDEX idx_pool_date ON stock_pool(date DESC);
CREATE INDEX idx_pool_decision ON stock_pool(date, final_decision);
CREATE INDEX idx_pool_strategy ON stock_pool(strategy_type, date DESC);
COMMENT ON TABLE stock_pool IS '每日股票池，记录筛选全流程结果';

CREATE TABLE strategy_params (
    id              SERIAL          PRIMARY KEY,
    strategy_type   VARCHAR(20)     NOT NULL,
    param_key       VARCHAR(50)     NOT NULL,
    param_value     TEXT            NOT NULL,
    param_type      VARCHAR(20)     NOT NULL DEFAULT 'string',
    description     TEXT,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(strategy_type, param_key)
);

CREATE TABLE backtest_results (
    id              BIGSERIAL       PRIMARY KEY,
    strategy_type   VARCHAR(20)     NOT NULL,
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    initial_capital NUMERIC(18,2)   NOT NULL,
    final_capital   NUMERIC(18,2)   NOT NULL,
    annual_return   NUMERIC(8,4),
    max_drawdown    NUMERIC(8,4),
    win_rate        NUMERIC(8,4),
    profit_loss_ratio NUMERIC(8,4),
    total_trades    INTEGER,
    params_used     JSONB           NOT NULL,
    daily_equity    JSONB,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_type, start_date DESC);

-- ============================================================================
-- DD-04: AI Agent 模块
-- ============================================================================

CREATE TABLE agent_discussions (
    id              BIGSERIAL       PRIMARY KEY,
    date            DATE            NOT NULL,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    round_num       SMALLINT        NOT NULL DEFAULT 1,
    agent_name      VARCHAR(32)     NOT NULL,
    score           SMALLINT,
    buy_reasons     JSONB           NOT NULL DEFAULT '[]',
    against_reasons JSONB           NOT NULL DEFAULT '[]',
    confidence      NUMERIC(4,2)    DEFAULT 0.5,
    prompt_tokens   INTEGER         DEFAULT 0,
    completion_tokens INTEGER       DEFAULT 0,
    model_name      VARCHAR(32),
    is_valid        BOOLEAN         NOT NULL DEFAULT TRUE,
    invalid_reason  VARCHAR(64),
    predicted_outcome VARCHAR(16),
    actual_outcome  VARCHAR(16),
    outcome_updated_at TIMESTAMPTZ,
    raw_response    TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_agent_disc_date_stock ON agent_discussions(date DESC, stock_code);
CREATE INDEX idx_agent_disc_agent ON agent_discussions(agent_name, date DESC);
CREATE INDEX idx_agent_disc_outcome ON agent_discussions(predicted_outcome, actual_outcome)
    WHERE predicted_outcome IS NOT NULL;
COMMENT ON TABLE agent_discussions IS 'Agent讨论记录';

CREATE TABLE agent_weights (
    id              BIGSERIAL       PRIMARY KEY,
    agent_name      VARCHAR(32)     NOT NULL,
    market_state    VARCHAR(16)     NOT NULL,
    base_weight     NUMERIC(4,2)    NOT NULL,
    calib_factor    NUMERIC(4,2)    NOT NULL DEFAULT 1.0,
    effective_weight NUMERIC(4,2)   NOT NULL,
    win_rate        NUMERIC(5,4)    DEFAULT 0.5,
    recent_count    INTEGER         DEFAULT 0,
    extreme_count   INTEGER         DEFAULT 0,
    is_degraded     BOOLEAN         DEFAULT FALSE,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_agent_weight UNIQUE (agent_name, market_state),
    CONSTRAINT chk_calib_factor CHECK (calib_factor >= 0.3 AND calib_factor <= 1.3),
    CONSTRAINT chk_base_weight CHECK (base_weight > 0 AND base_weight <= 1.0)
);
COMMENT ON TABLE agent_weights IS 'Agent权重配置与校准';

CREATE TABLE agent_decisions (
    id              BIGSERIAL       PRIMARY KEY,
    date            DATE            NOT NULL,
    stock_code      VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    total_score     NUMERIC(6,2),
    buy_score_sum   NUMERIC(6,2),
    against_score_sum NUMERIC(6,2),
    net_score       NUMERIC(6,2),
    decision        VARCHAR(16)    NOT NULL,
    decision_reason TEXT,
    agent_votes_json JSONB        NOT NULL DEFAULT '{}',
    risk_veto       BOOLEAN       DEFAULT FALSE,
    risk_veto_reason VARCHAR(128),
    convergence_rounds SMALLINT   DEFAULT 0,
    convergence_method VARCHAR(32),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_decision UNIQUE (date, stock_code)
);
CREATE INDEX idx_agent_dec_date ON agent_decisions(date DESC);
COMMENT ON TABLE agent_decisions IS '最终加权投票决策';

CREATE TABLE llm_usage (
    id                SERIAL        PRIMARY KEY,
    date              DATE          NOT NULL,
    model             VARCHAR(32)   NOT NULL,
    agent_name        VARCHAR(32),
    prompt_tokens     INTEGER       DEFAULT 0,
    completion_tokens INTEGER       DEFAULT 0,
    total_cost        DECIMAL(10,4) DEFAULT 0,
    call_count        INTEGER       DEFAULT 1,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_llm_usage UNIQUE (date, model, agent_name)
);
CREATE INDEX idx_llm_usage_date ON llm_usage(date DESC);
CREATE INDEX idx_llm_usage_model ON llm_usage(model, date DESC);
COMMENT ON TABLE llm_usage IS 'LLM Token用量监控';

CREATE TABLE agent_prompts (
    id              BIGSERIAL       PRIMARY KEY,
    agent_name      VARCHAR(32)     NOT NULL,
    version         VARCHAR(16)     NOT NULL,
    system_prompt   TEXT            NOT NULL,
    user_prompt_template TEXT       NOT NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT FALSE,
    change_note     TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_agent_prompt_version UNIQUE (agent_name, version)
);
COMMENT ON TABLE agent_prompts IS 'Agent提示词版本管理';

-- ============================================================================
-- DD-05: 交易执行模块
-- ============================================================================

CREATE TABLE trade_orders (
    id                BIGSERIAL       PRIMARY KEY,
    client_order_id   VARCHAR(64)     NOT NULL,
    stock_code        VARCHAR(10)     NOT NULL REFERENCES stocks(code),
    direction         VARCHAR(10)     NOT NULL,
    order_type        VARCHAR(20)     NOT NULL,
    price             NUMERIC(18,4),
    volume            INTEGER         NOT NULL,
    filled_volume     INTEGER         NOT NULL DEFAULT 0,
    filled_amount     NUMERIC(18,4)   NOT NULL DEFAULT 0,
    status            VARCHAR(20)     NOT NULL DEFAULT 'pending',
    retry_count       INTEGER         NOT NULL DEFAULT 0,
    max_retry         INTEGER         NOT NULL DEFAULT 3,
    position_batch    VARCHAR(20),
    trigger_source    VARCHAR(20)     NOT NULL,
    trade_mode        VARCHAR(20)     NOT NULL,
    broker_order_id   VARCHAR(64),
    strategy_type     VARCHAR(20),
    reason            TEXT,
    agent_scores_json JSONB           DEFAULT '{}',
    stop_loss_price   NUMERIC(18,4),
    stop_profit_pct   NUMERIC(8,4),
    error_message     TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(client_order_id)
);
CREATE INDEX idx_orders_stock ON trade_orders(stock_code, created_at DESC);
CREATE INDEX idx_orders_status ON trade_orders(status, created_at DESC);
CREATE INDEX idx_orders_date ON trade_orders(created_at DESC);
CREATE INDEX idx_orders_broker ON trade_orders(broker_order_id) WHERE broker_order_id IS NOT NULL;
COMMENT ON TABLE trade_orders IS '交易订单，全链路记录每笔交易';

CREATE TABLE positions (
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
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(stock_code)  -- 活跃持仓唯一（使用部分索引）
);
CREATE INDEX idx_positions_stock ON positions(stock_code);
CREATE INDEX idx_positions_active ON positions(id) WHERE total_volume > 0;
CREATE INDEX idx_positions_cooling ON positions(stock_code) WHERE is_cooling_down = TRUE;
COMMENT ON TABLE positions IS '持仓管理，推进式仓位分批建仓';

CREATE TABLE stop_loss_conditions (
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
CREATE INDEX idx_stoploss_position ON stop_loss_conditions(position_id);
CREATE INDEX idx_stoploss_stock ON stop_loss_conditions(stock_code, is_active);
CREATE INDEX idx_stoploss_active ON stop_loss_conditions(id) WHERE is_active = TRUE;
COMMENT ON TABLE stop_loss_conditions IS '止损条件';

CREATE TABLE trade_mode (
    id                SERIAL          PRIMARY KEY,
    current_mode      VARCHAR(20)     NOT NULL DEFAULT 'SIMULATION',
    confirm_mode      VARCHAR(20)     NOT NULL DEFAULT 'advisory',
    mode_password_hash VARCHAR(255),
    upgraded_at       TIMESTAMPTZ,
    emergency_stop    BOOLEAN         NOT NULL DEFAULT FALSE,
    emergency_stopped_at TIMESTAMPTZ,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE stop_profit_conditions (
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
CREATE INDEX idx_stopprofit_position ON stop_profit_conditions(position_id);
CREATE INDEX idx_stopprofit_active ON stop_profit_conditions(id) WHERE is_active = TRUE;
COMMENT ON TABLE stop_profit_conditions IS '阶梯止盈条件';

CREATE TABLE account_sync_log (
    id                BIGSERIAL       PRIMARY KEY,
    sync_type         VARCHAR(20)     NOT NULL,
    total_asset       NUMERIC(18,4),
    available_cash    NUMERIC(18,4),
    frozen_cash       NUMERIC(18,4),
    daily_pnl         NUMERIC(18,4),
    positions_json    JSONB,
    sync_status       VARCHAR(10)     NOT NULL DEFAULT 'success',
    error_message     TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_account_sync_type ON account_sync_log(sync_type, created_at DESC);
COMMENT ON TABLE account_sync_log IS '账户资产同步记录';

-- ============================================================================
-- DD-06: 风险监控模块
-- ============================================================================

CREATE TABLE risk_events (
    id              BIGSERIAL       PRIMARY KEY,
    event_type      VARCHAR(40)     NOT NULL,
    event_level     VARCHAR(20)     NOT NULL,
    trigger_value   NUMERIC(18,4),
    threshold_value NUMERIC(18,4),
    trigger_reason  TEXT            NOT NULL,
    action_taken    VARCHAR(40)     NOT NULL,
    action_detail   JSONB           DEFAULT '{}',
    recovery_path   VARCHAR(10),
    recovery_status VARCHAR(20)     DEFAULT 'pending',
    recovery_deadline DATE,
    resolved_at     TIMESTAMPTZ,
    trade_date      DATE            NOT NULL,
    is_intraday     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_risk_events_date ON risk_events(trade_date DESC);
CREATE INDEX idx_risk_events_type ON risk_events(event_type, trade_date DESC);
CREATE INDEX idx_risk_events_level ON risk_events(event_level, trade_date DESC);
CREATE INDEX idx_risk_events_recovery ON risk_events(recovery_status, recovery_path)
    WHERE recovery_status != 'resolved';
COMMENT ON TABLE risk_events IS '风控事件记录';

CREATE TABLE risk_metrics_daily (
    id              BIGSERIAL       PRIMARY KEY,
    trade_date      DATE            NOT NULL,
    daily_drawdown  NUMERIC(8,4),
    max_drawdown    NUMERIC(8,4),
    win_rate        NUMERIC(8,4),
    win_rate_3d     NUMERIC(8,4),
    consecutive_loss_days INTEGER   DEFAULT 0,
    profit_loss_ratio NUMERIC(8,4),
    pl_ratio_rolling NUMERIC(8,4),
    consecutive_losses INTEGER    DEFAULT 0,
    total_position_pct NUMERIC(8,4),
    position_count INTEGER         DEFAULT 0,
    annual_return   NUMERIC(8,4),
    sharpe_ratio    NUMERIC(8,4),
    calmar_ratio    NUMERIC(8,4),
    market_daily_change NUMERIC(8,4),
    qmt_failure_count INTEGER      DEFAULT 0,
    risk_status     VARCHAR(20)     DEFAULT 'normal',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(trade_date)
);
CREATE INDEX idx_risk_metrics_date ON risk_metrics_daily(trade_date DESC);
COMMENT ON TABLE risk_metrics_daily IS '每日风控指标快照';

CREATE TABLE recovery_plans (
    id              BIGSERIAL       PRIMARY KEY,
    risk_event_id   BIGINT          NOT NULL REFERENCES risk_events(id),
    path_type       VARCHAR(10)     NOT NULL,
    agent_diagnosis TEXT,
    backtest_result JSONB,
    param_changes   JSONB,
    degraded_mode_end DATE,
    cold_start_date DATE,
    cold_start_result JSONB,
    status          VARCHAR(20)     DEFAULT 'pending',
    approved_by     VARCHAR(50),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE layer_outputs (
    id              BIGSERIAL       PRIMARY KEY,
    review_date     DATE            NOT NULL,
    layer_num       SMALLINT        NOT NULL,
    layer_name      VARCHAR(40)     NOT NULL,
    decision        VARCHAR(20)     NOT NULL,
    decision_detail TEXT,
    agent_votes     JSONB,
    backtest_result JSONB,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(review_date, layer_num)
);
COMMENT ON TABLE layer_outputs IS '分层回溯验证的各层输出';

-- ============================================================================
-- DD-07: 经验库模块
-- ============================================================================

CREATE TABLE experiences (
    id              BIGSERIAL       PRIMARY KEY,
    market_state    VARCHAR(20)     NOT NULL,
    sector          VARCHAR(32),
    strategy_type   VARCHAR(20)     NOT NULL,
    stock_code      VARCHAR(10),
    operation       VARCHAR(20)     NOT NULL,
    operation_detail JSONB          DEFAULT '{}',
    result          VARCHAR(20)     NOT NULL,
    pnl_pct         NUMERIC(8,4),
    holding_days    INTEGER,
    score           NUMERIC(6,2)     NOT NULL,
    confidence      NUMERIC(4,2)     NOT NULL DEFAULT 50.0,
    tags            JSONB           DEFAULT '[]',
    scenario_hash   VARCHAR(64)     NOT NULL,
    source          VARCHAR(20)     NOT NULL DEFAULT 'real',
    source_id       BIGINT,
    is_archived     BOOLEAN         NOT NULL DEFAULT FALSE,
    last_verified_at TIMESTAMPTZ,
    weight          NUMERIC(4,2)     NOT NULL DEFAULT 100.0,
    related_trade_id BIGINT,
    feedback_text   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(scenario_hash)
);
CREATE INDEX idx_experiences_market_state ON experiences(market_state, created_at DESC);
CREATE INDEX idx_experiences_strategy ON experiences(strategy_type, created_at DESC);
CREATE INDEX idx_experiences_sector ON experiences(sector, created_at DESC);
CREATE INDEX idx_experiences_source ON experiences(source, created_at DESC);
CREATE INDEX idx_experiences_score ON experiences(score DESC) WHERE is_archived = FALSE;
CREATE INDEX idx_experiences_scenario ON experiences(scenario_hash) WHERE is_archived = FALSE;
CREATE INDEX idx_experiences_active ON experiences(market_state, strategy_type, is_archived)
    WHERE is_archived = FALSE AND weight > 0;
COMMENT ON TABLE experiences IS '经验记录';

CREATE TABLE param_change_log (
    id              BIGSERIAL       PRIMARY KEY,
    strategy_type   VARCHAR(20)     NOT NULL,
    param_key       VARCHAR(50)     NOT NULL,
    old_value       TEXT            NOT NULL,
    new_value       TEXT            NOT NULL,
    reason          TEXT            NOT NULL,
    suggestion_type VARCHAR(20),
    source_experience_ids JSONB     DEFAULT '[]',
    changed_by      VARCHAR(20)     NOT NULL DEFAULT 'system_suggest',
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
    wechat_msg_id   VARCHAR(64),
    approved_at     TIMESTAMPTZ,
    approved_by     VARCHAR(50),
    reject_reason   TEXT,
    backtest_id     BIGINT,
    backtest_passed BOOLEAN,
    backtest_detail JSONB,
    effective_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_param_change_status ON param_change_log(status, created_at DESC);
CREATE INDEX idx_param_change_param ON param_change_log(strategy_type, param_key, created_at DESC);
CREATE INDEX idx_param_change_pending ON param_change_log(created_at DESC)
    WHERE status = 'pending';
COMMENT ON TABLE param_change_log IS '参数变更审计日志';

CREATE TABLE experience_feedback (
    id              BIGSERIAL       PRIMARY KEY,
    experience_id   BIGINT          NOT NULL REFERENCES experiences(id),
    feedback_type   VARCHAR(20)     NOT NULL,
    feedback_text   TEXT            NOT NULL,
    suggested_action VARCHAR(20),
    is_processed    BOOLEAN         NOT NULL DEFAULT FALSE,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_feedback_unprocessed ON experience_feedback(created_at DESC)
    WHERE is_processed = FALSE;

-- ============================================================================
-- DD-09: Hermes 消息推送模块
-- ============================================================================

CREATE TABLE notifications (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id),
    event_type      VARCHAR(40)     NOT NULL,
    priority        VARCHAR(10)     NOT NULL DEFAULT 'normal',
    title           VARCHAR(200)    NOT NULL,
    content         TEXT            NOT NULL,
    content_json    JSONB           DEFAULT '{}',
    push_channel    VARCHAR(20)     NOT NULL DEFAULT 'wechat',
    push_status     VARCHAR(20)     NOT NULL DEFAULT 'pending',
    wechat_msg_id   VARCHAR(100),
    confirm_type    VARCHAR(20)     DEFAULT 'none',
    confirm_status  VARCHAR(20)     DEFAULT 'none',
    confirm_payload JSONB           DEFAULT '{}',
    confirm_reply   TEXT,
    confirm_at      TIMESTAMPTZ,
    expire_at       TIMESTAMPTZ,
    retry_count     SMALLINT        NOT NULL DEFAULT 0,
    max_retry       SMALLINT        NOT NULL DEFAULT 3,
    last_retry_at   TIMESTAMPTZ,
    dedup_key       VARCHAR(100),
    is_read         BOOLEAN         NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(event_type, created_at DESC);
CREATE INDEX idx_notifications_status ON notifications(push_status, priority)
    WHERE push_status IN ('pending', 'retrying');
CREATE INDEX idx_notifications_confirm ON notifications(confirm_status, expire_at)
    WHERE confirm_status = 'pending';
CREATE INDEX idx_notifications_dedup ON notifications(dedup_key, created_at DESC)
    WHERE dedup_key IS NOT NULL;
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE is_read = FALSE;
COMMENT ON TABLE notifications IS '通知记录';

CREATE TABLE push_config (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id),
    event_type      VARCHAR(40)     NOT NULL,
    is_enabled      BOOLEAN         NOT NULL DEFAULT TRUE,
    push_channel    VARCHAR(20)     NOT NULL DEFAULT 'both',
    quiet_hours_start TIME,
    quiet_hours_end   TIME,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, event_type)
);
COMMENT ON TABLE push_config IS '推送事件配置';

CREATE TABLE notification_templates (
    id              SERIAL          PRIMARY KEY,
    event_type      VARCHAR(40)     NOT NULL,
    template_name   VARCHAR(100)    NOT NULL,
    title_template  VARCHAR(200)    NOT NULL,
    body_template   TEXT            NOT NULL,
    json_schema     JSONB           DEFAULT '{}',
    priority        VARCHAR(10)     NOT NULL,
    confirm_type    VARCHAR(20)     DEFAULT 'none',
    confirm_expire_minutes INTEGER  DEFAULT 0,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(event_type, template_name, version)
);
COMMENT ON TABLE notification_templates IS '消息推送模板';

-- ============================================================================
-- 验证建表结果
-- ============================================================================
SELECT 'tables_created' AS status, COUNT(*) AS count
FROM information_schema.tables
WHERE table_schema = 'public';
