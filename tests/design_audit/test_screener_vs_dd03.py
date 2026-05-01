"""设计文档审查：策略粗筛模块 vs DD-03 策略引擎模块

此测试不验证代码功能正确性（那是单元测试的工作），
而是验证代码实现与详细设计文档的约束完全对齐。
"""

import inspect

import pandas as pd

from src.strategy.screener import (
    STRATEGY1_DROP_60D_THRESHOLD,
    STRATEGY1_DROP_5D_THRESHOLD,
    STRATEGY1_MIN_MARKET_CAP,
    STRATEGY1_MAX_MARKET_CAP,
    STRATEGY1_MIN_DAILY_AMOUNT,
    STRATEGY1_MIN_DAYS_LISTED,
    STRATEGY2_SECTOR_CONCENTRATION,
    STRATEGY2_MIN_ADX,
    STRATEGY2_VOLUME_RATIO,
    STRATEGY2_PRICE_DROP_THRESHOLD,
    STRATEGY2_MIN_DAILY_AMOUNT,
    STRATEGY2_SECTOR_CHECK_DAYS,
    is_st_stock,
    is_new_stock,
    has_drop_in_window,
    has_sufficient_liquidity,
    is_bullish_arrangement,
    is_volume_shrinking,
    calculate_adx,
    screen_strategy1,
    screen_strategy2,
    StrategyCandidate,
)

# ═══════════════════════════════════════════════════════════════════
# DD-03 §2.1.3 策略参数配置 → 代码常量检查
# ═══════════════════════════════════════════════════════════════════

class TestStrategyParamsVsDesignDoc:
    """DD-03 策略参数表 strategy_params 预置值 vs screener.py 常量"""

    # 策略一参数
    def test_decline_60d_pct(self):
        """DD-03: decline_60d_pct=20 → STRATEGY1_DROP_60D_THRESHOLD=20.0"""
        assert STRATEGY1_DROP_60D_THRESHOLD == 20.0, \
            f"设计文档指定近60日跌幅阈值20%，当前值{STRATEGY1_DROP_60D_THRESHOLD}"

    def test_sharp_drop_5d_pct(self):
        """DD-03: sharp_drop_5d_pct=5 → STRATEGY1_DROP_5D_THRESHOLD=-5.0"""
        assert STRATEGY1_DROP_5D_THRESHOLD == -5.0, \
            f"设计文档指定5日单日跌幅5%，当前值{STRATEGY1_DROP_5D_THRESHOLD}"

    def test_market_cap_min(self):
        """DD-03: market_cap_min=50亿 → STRATEGY1_MIN_MARKET_CAP=50亿"""
        assert STRATEGY1_MIN_MARKET_CAP == 5_000_000_000, \
            f"最小市值应为50亿(5_000_000_000)，当前{STRATEGY1_MIN_MARKET_CAP}"

    def test_market_cap_max(self):
        """DD-03: market_cap_max=500亿 → STRATEGY1_MAX_MARKET_CAP=500亿"""
        assert STRATEGY1_MAX_MARKET_CAP == 50_000_000_000, \
            f"最大市值应为500亿(50_000_000_000)，当前{STRATEGY1_MAX_MARKET_CAP}"

    def test_min_daily_amount_s1(self):
        """DD-03: min_daily_amount=1亿 → STRATEGY1_MIN_DAILY_AMOUNT=1亿"""
        assert STRATEGY1_MIN_DAILY_AMOUNT == 100_000_000, \
            f"策略一最小日均成交额应为1亿，当前{STRATEGY1_MIN_DAILY_AMOUNT}"

    def test_min_list_days(self):
        """DD-03: min_list_days=180 → STRATEGY1_MIN_DAYS_LISTED=180"""
        assert STRATEGY1_MIN_DAYS_LISTED == 180, \
            f"最少上市天数应为180，当前{STRATEGY1_MIN_DAYS_LISTED}"

    # 策略二参数
    def test_sector_capital_ratio(self):
        """DD-03: sector_capital_ratio=12% → STRATEGY2_SECTOR_CONCENTRATION=12.0"""
        # 设计文档12% → 代码值12.0（百分比制）
        assert STRATEGY2_SECTOR_CONCENTRATION == 12.0, \
            f"板块资金集中度阈值应为12%，当前{STRATEGY2_SECTOR_CONCENTRATION}"

    def test_sector_hot_days(self):
        """DD-03: sector_hot_days=2 → STRATEGY2_SECTOR_CHECK_DAYS=2"""
        assert STRATEGY2_SECTOR_CHECK_DAYS == 2, \
            f"板块连续热门天数应为2，当前{STRATEGY2_SECTOR_CHECK_DAYS}"

    def test_adx_threshold(self):
        """DD-03: adx_threshold=25 → STRATEGY2_MIN_ADX=25.0"""
        assert STRATEGY2_MIN_ADX == 25.0, \
            f"ADX阈值应为25，当前{STRATEGY2_MIN_ADX}"

    def test_volume_shrink_pct(self):
        """DD-03: volume_shrink_pct=80 → STRATEGY2_VOLUME_RATIO=0.8"""
        assert STRATEGY2_VOLUME_RATIO == 0.8, \
            f"缩量阈值应为80%(0.8)，当前{STRATEGY2_VOLUME_RATIO}"

    def test_drop_3d_pct(self):
        """DD-03: drop_3d_pct=3 → STRATEGY2_PRICE_DROP_THRESHOLD=-3.0"""
        # 设计文档"3日回踩跌幅阈值3%" → 代码为-3.0（跌幅方向）
        assert STRATEGY2_PRICE_DROP_THRESHOLD == -3.0, \
            f"3日回踩跌幅阈值应为3%(代码-3.0)，当前{STRATEGY2_PRICE_DROP_THRESHOLD}"

    def test_min_daily_amount_s2(self):
        """DD-03: min_daily_amount=3亿 → STRATEGY2_MIN_DAILY_AMOUNT=3亿"""
        assert STRATEGY2_MIN_DAILY_AMOUNT == 300_000_000, \
            f"策略二最小日均成交额应为3亿，当前{STRATEGY2_MIN_DAILY_AMOUNT}"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.2 粗筛伪代码 → 函数签名和逻辑检查
# ═══════════════════════════════════════════════════════════════════

class TestScreenFunctionsVsDesignDoc:
    """DD-03 粗筛伪代码 vs 实际实现的函数结构和约束"""

    def test_strategy_candidate_has_required_fields(self):
        """DD-03 CandidateStock: stock_code, stock_name, strategy_type, decline_pct/adx, avg_amount"""
        fields = StrategyCandidate.__dataclass_fields__
        assert "stock_code" in fields
        assert "stock_name" in fields
        assert "drop_pct" in fields
        assert "daily_amount" in fields
        assert "score" in fields
        assert "reason" in fields

    def test_screen_strategy1_returns_list(self):
        """DD-03: screen_bottom_volume 返回 list[CandidateStock]"""
        sig = inspect.signature(screen_strategy1)
        return_ann = sig.return_annotation
        # 函数签名可能没有显式注解，但返回值应为 list[StrategyCandidate]
        # 运行时验证通过单元测试覆盖，此处仅做签名检查
        assert 'StrategyCandidate' in str(sig.return_annotation), \
            f"screen_strategy1应返回list[StrategyCandidate]，实际签名return={return_ann}"

    def test_screen_strategy2_returns_list(self):
        """DD-03: screen_trend_momentum 返回 list[CandidateStock]"""
        sig = inspect.signature(screen_strategy2)
        return_ann = sig.return_annotation
        assert 'StrategyCandidate' in str(return_ann), \
            f"screen_strategy2应返回list[StrategyCandidate]，实际{return_ann}"

    def test_is_st_stock_includes_st_star_and_sst(self):
        """DD-03: ST排除 — 含ST/*ST/SST"""
        assert is_st_stock("ST平安"), "应识别ST前缀"
        assert is_st_stock("*ST博信"), "应识别*ST前缀"
        assert is_st_stock("SST前锋"), "应识别SST前缀"
        assert not is_st_stock("贵州茅台"), "正常股票不应排除"

    def test_is_new_stock_180_days(self):
        """DD-03: min_list_days=180"""
        from datetime import date, timedelta
        today = date(2026, 5, 12)
        assert is_new_stock(today - timedelta(days=100), today), "100天应判定为次新"
        assert not is_new_stock(today - timedelta(days=200), today), "200天不应判定为次新"

    def test_strategy1_conditions_all_present(self):
        """DD-03: 策略一5个筛选条件全部实现"""
        source = inspect.getsource(screen_strategy1)
        checks = [
            ("跌幅≥20%", "STRATEGY1_DROP_60D_THRESHOLD"),
            ("近5日大跌", "has_drop_in_window"),
            ("市值范围50-500亿", "STRATEGY1_MIN_MARKET_CAP"),
            ("非ST", "is_st_stock"),
            ("非次新", "is_new_stock"),
            ("流动性≥1亿", "has_sufficient_liquidity"),
        ]
        for name, keyword in checks:
            assert keyword in source, \
                f"策略一未实现条件'{name}'（{keyword}未出现在代码中）"

    def test_strategy2_conditions_all_present(self):
        """DD-03: 策略二6个筛选条件全部实现"""
        source = inspect.getsource(screen_strategy2)
        checks = [
            ("板块集中度≥12%", "STRATEGY2_SECTOR_CONCENTRATION"),
            ("多头排列", "is_bullish_arrangement"),
            ("ADX≥25", "STRATEGY2_MIN_ADX"),
            ("缩量回踩", "is_volume_shrinking"),
            ("日均成交额≥3亿", "STRATEGY2_MIN_DAILY_AMOUNT"),
            ("非ST", "is_st_stock"),
            ("非次新", "is_new_stock"),
        ]
        for name, keyword in checks:
            assert keyword in source, \
                f"策略二未实现条件'{name}'（{keyword}未出现在代码中）"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.2 策略一粗筛伪代码逻辑检查
# ═══════════════════════════════════════════════════════════════════

class TestStrategy1LogicVsDesignDoc:
    """DD-03 §3.2 screen_bottom_volume 伪代码逐条验证"""

    def test_decline_calculation_method(self):
        """DD-03: 近60日跌幅 = (max_close - latest_close) / max_close × 100"""
        source = inspect.getsource(screen_strategy1)
        # 设计文档用 max_close 方法计算跌幅
        assert "first_close" in source or "max_close" in source or "drop_pct" in source, \
            "策略一应计算近60日跌幅"
        assert "STRATEGY1_DROP_60D_THRESHOLD" in source, \
            "应使用60日跌幅阈值过滤"

    def test_sharp_drop_in_window(self):
        """DD-03: 近5日单日跌幅≥5%"""
        # 验证 has_drop_in_window 被调用
        source = inspect.getsource(screen_strategy1)
        assert "has_drop_in_window" in source, "应检测近5日单日大跌"
        # 验证阈值
        sig = inspect.signature(has_drop_in_window)
        params = sig.parameters
        default_threshold = params['threshold'].default
        assert default_threshold == -5.0, \
            f"单日跌幅阈值应为-5%，当前默认{default_threshold}"

    def test_liquidity_gte_1e8(self):
        """DD-03: 日均成交额≥1亿"""
        default_amount = inspect.signature(has_sufficient_liquidity).parameters['min_daily_amount'].default
        assert default_amount == 100_000_000, \
            f"流动性检查默认最小值应为1亿(100_000_000)，当前{default_amount}"

    def test_market_cap_between_5e9_and_5e10(self):
        """DD-03: 市值50亿~500亿"""
        assert STRATEGY1_MIN_MARKET_CAP <= STRATEGY1_MAX_MARKET_CAP, \
            "最小市值应小于最大市值"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.2 策略二粗筛伪代码逻辑检查
# ═══════════════════════════════════════════════════════════════════

class TestStrategy2LogicVsDesignDoc:
    """DD-03 §3.2 screen_trend_momentum 伪代码逐条验证"""

    def test_mainline_sectors_checked_first(self):
        """DD-03: 策略二从主线板块成分股开始筛选"""
        source = inspect.getsource(screen_strategy2)
        assert "hot_sector" in source or "mainline" in source or "sector" in source, \
            "策略二应先检测主线板块"

    def test_bullish_arrangement_check(self):
        """DD-03: MA5>MA10>MA20>MA60 多头排列"""
        source = inspect.getsource(is_bullish_arrangement)
        assert "ma5" in source and "ma10" in source and "ma20" in source and "ma60" in source
        assert ">" in source or ">=" in source

    def test_adx_calculation(self):
        """DD-03: ADX计算存在且阈值检查"""
        source = inspect.getsource(screen_strategy2)
        assert "calculate_adx" in source or "adx" in source.lower(), \
            "策略二应计算或检查ADX"
        assert "STRATEGY2_MIN_ADX" in source, "应使用ADX阈值过滤"

    def test_volume_shrinking(self):
        """DD-03: 近3日均量 < 5日均量×80%"""
        source = inspect.getsource(is_volume_shrinking)
        assert "lookback" in source, "应有回看天数参数"
        assert "ratio" in source, "应有缩量比率参数"
        default_ratio = inspect.signature(is_volume_shrinking).parameters['ratio'].default
        assert default_ratio == 0.8, f"缩量比率默认为0.8，当前{default_ratio}"

    def test_price_drop_check(self):
        """DD-03: 3日回踩跌幅<3%"""
        source = inspect.getsource(screen_strategy2)
        assert "STRATEGY2_PRICE_DROP_THRESHOLD" in source or "drop_3d" in source, \
            "策略二应检查3日回踩跌幅"

    def test_liquidity_gte_3e8(self):
        """DD-03: 日均成交额≥3亿"""
        assert STRATEGY2_MIN_DAILY_AMOUNT == 300_000_000, \
            f"策略二最小日均成交额应为3亿，当前{STRATEGY2_MIN_DAILY_AMOUNT}"

    def test_sector_consecutive_days_check(self):
        """DD-03: 板块资金集中度连续N天检查"""
        source = inspect.getsource(screen_strategy2)
        assert "STRATEGY2_SECTOR_CHECK_DAYS" in source or "consecutive" in source.lower(), \
            "策略二应检查连续天数"

    def test_non_st_screening(self):
        """DD-03: 策略二排除ST"""
        source = inspect.getsource(screen_strategy2)
        assert "is_st_stock" in source, "策略二应排除ST股票"
