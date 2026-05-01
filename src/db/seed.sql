-- ============================================================================
-- FraxVerse · 种子数据初始化
-- ============================================================================

-- 补建缺失索引
CREATE INDEX IF NOT EXISTS idx_positions_active ON positions(id) WHERE total_volume > 0;
CREATE INDEX IF NOT EXISTS idx_positions_cooling ON positions(stock_code) WHERE is_cooling_down = TRUE;

-- 交易模式初始行（单行表）
INSERT INTO trade_mode (current_mode, confirm_mode)
SELECT 'SIMULATION', 'advisory'
WHERE NOT EXISTS (SELECT 1 FROM trade_mode);

-- 系统配置
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('system_initialized', 'false', 'bool', '系统是否已完成首次初始化'),
('trade_mode', 'simulation', 'string', '交易模式：simulation/paper/live'),
('data_source_akshare', 'true', 'bool', '是否启用AKShare数据源')
ON CONFLICT (config_key) DO NOTHING;

-- 策略参数
INSERT INTO strategy_params (strategy_type, param_key, param_value, param_type, description) VALUES
-- 策略一
('bottom_volume', 'decline_60d_pct', '20', 'int', '近60日跌幅阈值(%)'),
('bottom_volume', 'sharp_drop_5d_pct', '5', 'int', '近5日单日跌幅阈值(%)'),
('bottom_volume', 'market_cap_min', '50', 'int', '最小市值(亿)'),
('bottom_volume', 'market_cap_max', '500', 'int', '最大市值(亿)'),
('bottom_volume', 'min_daily_amount', '1', 'int', '日均成交额最小值(亿)'),
('bottom_volume', 'min_list_days', '180', 'int', '最少上市天数'),
-- 策略二
('trend_momentum', 'sector_capital_ratio', '12', 'int', '板块资金集中度阈值(%)'),
('trend_momentum', 'sector_hot_days', '2', 'int', '板块连续热门天数'),
('trend_momentum', 'adx_threshold', '25', 'int', 'ADX趋势强度阈值'),
('trend_momentum', 'volume_shrink_pct', '80', 'int', '缩量回踩阈值(%)'),
('trend_momentum', 'drop_3d_pct', '3', 'int', '3日回踩跌幅阈值(%)'),
('trend_momentum', 'min_daily_amount', '3', 'int', '日均成交额最小值(亿)'),
-- 公共
('common', 'state_cooldown_days', '3', 'int', '状态切换冷却期(天)'),
('common', 'max_main_lines', '2', 'int', '最大主线并行数'),
('common', 'oscillation_threshold', '3', 'int', '震荡保护来回切换次数'),
('common', 'max_position_per_stock', '30', 'int', '单票最大仓位(%)'),
('common', 'premarket_gap_pct', '3', 'int', '开盘前复核跳空阈值(%)')
ON CONFLICT (strategy_type, param_key) DO NOTHING;

-- Agent权重配置
INSERT INTO agent_weights (agent_name, market_state, base_weight, calib_factor, effective_weight) VALUES
-- 主线行情
('mainline_hunter',  '主线确认', 0.35, 1.0, 0.35),
('fund_detective',   '主线确认', 0.25, 1.0, 0.25),
('sentiment_catcher','主线确认', 0.15, 1.0, 0.15),
('experience_judge', '主线确认', 0.25, 1.0, 0.25),
-- 震荡市
('mainline_hunter',  '非主线状态', 0.20, 1.0, 0.20),
('fund_detective',   '非主线状态', 0.25, 1.0, 0.25),
('sentiment_catcher','非主线状态', 0.20, 1.0, 0.20),
('experience_judge', '非主线状态', 0.35, 1.0, 0.35)
ON CONFLICT (agent_name, market_state) DO NOTHING;

SELECT 'seed_complete' AS status, COUNT(*) AS tables_count
FROM information_schema.tables WHERE table_schema='public';
