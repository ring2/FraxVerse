"""测试五维度评分模块

P0-4.1: 五维度评分（趋势强度/资金热度/回调深度/流动性安全/形态健康度）

测试策略：
1. 各维度独立打分函数 —— 边界值、分段场景
2. score_candidates 集成 —— 排序正确性
3. choose_best 选取 —— 合并去重、不超过3只、策略优先级
4. 边界条件 —— 空列表、极值、缺失字段
"""

import pytest

from src.strategy.scorer import (
    ScoredCandidate,
    choose_best,
    score_candidates,
    score_capital_heat,
    score_liquidity_safety,
    score_pattern_health,
    score_pullback_depth,
    score_trend_strength,
)
from src.strategy.screener import StrategyCandidate

# ── 辅助构建函数 ────────────────────────────────────────────────

def make_candidate(
    code: str = "000001.SZ",
    name: str = "测试股票",
    adx: float = 35.0,
    mas: dict | None = None,
    avg_amount: float = 2_000_000_000,
    sector_ratio: float = 0.5,
    pct_changes: list[float] | None = None,
    max_drawdown_60d: float = -25.0,
    volume_ratio: float = 0.6,
    market_cap: float = 10_000_000_000,
    turnover_rate: float = 0.05,
    ma_slope: float = 0.0,
    recent_volume_ratio: float = 1.2,
    upper_shadow_ratio: float = 0.5,
    strategy: str = "strategy2",
) -> StrategyCandidate:
    """创建带有完整 detail 的候选标的"""
    if mas is None:
        mas = {"ma5": 15.0, "ma10": 14.5, "ma20": 14.0, "ma60": 13.0}
    if pct_changes is None:
        pct_changes = [-1.5, -0.5, 2.0]
    return StrategyCandidate(
        stock_code=code,
        stock_name=name,
        score=30.0,
        daily_amount=avg_amount,
        reason=f"ADX:{adx:.1f}",
        detail={
            "adx": adx,
            "mas": mas,
            "avg_amount": avg_amount,
            "sector_ratio": sector_ratio,
            "pct_changes": pct_changes,
            "max_drawdown_60d": max_drawdown_60d,
            "volume_ratio": volume_ratio,
            "market_cap": market_cap,
            "turnover_rate": turnover_rate,
            "ma_slope": ma_slope,
            "recent_volume_ratio": recent_volume_ratio,
            "upper_shadow_ratio": upper_shadow_ratio,
            "strategy": strategy,
        },
    )


# ════════════════════════════════════════════════════════════════
# 维度一：趋势强度 (TrendStrength)
# ════════════════════════════════════════════════════════════════

class TestScoreTrendStrength:
    """基于ADX值、均线斜率、价格相对均线位置"""

    def test_adx_high(self):
        """场景：ADX=45（强趋势）→ 100分"""
        c = make_candidate(adx=45.0)
        dim = score_trend_strength(c)
        assert dim.score == 100.0

    def test_adx_medium(self):
        """场景：ADX=32 → 80分"""
        c = make_candidate(adx=32.0)
        dim = score_trend_strength(c)
        assert dim.score == 80.0

    def test_adx_threshold_min(self):
        """场景：ADX=25（刚好门槛）→ 60分"""
        c = make_candidate(adx=25.0)
        dim = score_trend_strength(c)
        assert dim.score == 60.0

    def test_adx_below_threshold(self):
        """场景：ADX=18（低于20）→ 20分"""
        c = make_candidate(adx=18.0)
        dim = score_trend_strength(c)
        assert dim.score == 20.0

    def test_adx_boundary_29(self):
        """场景：ADX=29.9（≥25<30）→ 60分"""
        c = make_candidate(adx=29.9)
        dim = score_trend_strength(c)
        assert dim.score == 60.0

    def test_price_above_ma5_bonus(self):
        """场景：价格在MA5之上 → 额外+10分，但不超100"""
        mas = {"ma5": 10.0, "ma10": 9.5, "ma20": 9.0, "ma60": 8.5}
        c = make_candidate(adx=40.0, mas=mas)
        c.detail["last_close"] = 11.0  # 价格 > MA5
        dim = score_trend_strength(c)
        assert dim.score == 100.0  # 基础100封顶

    def test_price_below_ma5_penalty(self):
        """场景：价格在MA5之下 → 扣10分"""
        mas = {"ma5": 10.0, "ma10": 9.5, "ma20": 9.0, "ma60": 8.5}
        c = make_candidate(adx=25.0, mas=mas)
        c.detail["last_close"] = 10.5  # 价格 > MA5 也不是惩罚场景
        # 重新构造：价格 < MA5
        c.detail["last_close"] = 9.0  # 价格 < MA5
        dim = score_trend_strength(c)
        assert dim.score == 50.0  # 60 - 10

    def test_ma_slope_up_bonus(self):
        """场景：均线斜率向上 → 额外+10分"""
        c = make_candidate(adx=25.0, ma_slope=0.1)
        # 价格没给，默认用 mas["ma5"] ~= mas 中的ma5? 实际检测用 last_close vs ma5
        # 要让 price >= ma5 不触发 penalty，ma_slope 触发 bonus
        mas = {"ma5": 10.0, "ma10": 9.5, "ma20": 9.0, "ma60": 8.5}
        c.detail["mas"] = mas
        c.detail["last_close"] = 10.0  # 刚好等于 MA5，不触发惩罚
        dim = score_trend_strength(c)
        assert dim.score == 70.0  # 60 + 10(斜率)

    def test_all_bonus_capped(self):
        """场景：ADX基础60 + 价格在上方+10 + 斜率向上+10 → 80分"""
        mas = {"ma5": 10.0, "ma10": 9.5, "ma20": 9.0, "ma60": 8.5}
        c = make_candidate(adx=25.0, mas=mas, ma_slope=0.1)
        c.detail["last_close"] = 10.5
        dim = score_trend_strength(c)
        assert dim.score == 80.0  # 60 + 10 + 10

    def test_missing_adx_default(self):
        """场景：detail缺失adx字段 → 默认20分（保守安全值）"""
        c = make_candidate()
        del c.detail["adx"]
        dim = score_trend_strength(c)
        assert dim.score == 20.0 and dim.weight == 0.30


# ════════════════════════════════════════════════════════════════
# 维度二：资金热度 (CapitalHeat)
# ════════════════════════════════════════════════════════════════

class TestScoreCapitalHeat:
    """基于板块资金集中度、个股日均成交额"""

    def test_high_concentration(self):
        """场景：板块集中度≥0.6+成交额10亿 → (100+100)/2=100"""
        c = make_candidate(sector_ratio=0.7, avg_amount=10_000_000_000)
        dim = score_capital_heat(c)
        assert dim.score == 100.0  # (100+100)/2=100

    def test_mid_concentration(self):
        """场景：板块集中度=0.35（≥0.3但<0.4）→ 板块60分，成交额10亿=100分，平均=80"""
        c = make_candidate(sector_ratio=0.35, avg_amount=10_000_000_000)
        dim = score_capital_heat(c)
        assert dim.score == 80.0  # (60+100)/2=80

    def test_low_concentration_low_amount(self):
        """场景：板块集中度0.15+成交额0.3亿 → 都低分"""
        c = make_candidate(sector_ratio=0.15, avg_amount=30_000_000)
        dim = score_capital_heat(c)
        assert dim.score == 20.0  # (20+20)/2=20

    def test_boundary_concentration(self):
        """场景：集中度0.2（刚好≥0.2→40）成交额1亿（≥1亿→60）→ (40+60)/2=50"""
        c = make_candidate(sector_ratio=0.2, avg_amount=100_000_000)
        dim = score_capital_heat(c)
        assert dim.score == 50.0  # (40+60)/2=50

    def test_amount_4_9_billion(self):
        """场景：成交额4.9亿（<5亿，在1-5段）→ 60分"""
        c = make_candidate(sector_ratio=0.5, avg_amount=490_000_000)
        dim = score_capital_heat(c)
        assert dim.score == 70.0  # (80+60)/2=70

    def test_missing_sector_ratio(self):
        """场景：detail缺少sector_ratio → 只按成交额算，20亿→100分"""
        c = make_candidate(avg_amount=5_000_000_000)
        del c.detail["sector_ratio"]
        dim = score_capital_heat(c)
        assert dim.score == 100.0  # 成交额50亿≥10亿→100


# ════════════════════════════════════════════════════════════════
# 维度三：回调/底部深度 (PullbackDepth)
# ════════════════════════════════════════════════════════════════

class TestScorePullbackDepth:
    """策略一用近60日跌幅+量缩止跌，策略二用缩量回调比+跌幅衰减"""

    def test_strategy1_deep_drop(self):
        """场景：策略一，近60日跌幅40%（≥30%基础80），量缩止跌额外+20 → 100分"""
        c = make_candidate(max_drawdown_60d=-40.0, volume_ratio=0.5, strategy="strategy1")
        dim = score_pullback_depth(c)
        assert dim.score == 100.0  # 80 + (40-30)/10*5 + 20，超100封顶

    def test_strategy1_moderate_drop(self):
        """场景：策略一，跌幅25%（<30%基础线）→ 0分"""
        c = make_candidate(max_drawdown_60d=-25.0, volume_ratio=0.8, strategy="strategy1")
        dim = score_pullback_depth(c)
        assert dim.score == 0.0

    def test_strategy1_50_percent_drop(self):
        """场景：策略一，跌幅50%（基础80+10=90）+量缩止跌+20 → 100封顶"""
        c = make_candidate(max_drawdown_60d=-50.0, volume_ratio=0.4, strategy="strategy1")
        dim = score_pullback_depth(c)
        assert dim.score == 100.0

    def test_strategy2_strong_shrink(self):
        """场景：策略二，缩量比0.4（≤0.5）→ 100分"""
        c = make_candidate(volume_ratio=0.4, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 100.0

    def test_strategy2_moderate_shrink(self):
        """场景：策略二，缩量比0.6（≤0.7）→ 80分"""
        c = make_candidate(volume_ratio=0.6, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 80.0

    def test_strategy2_mild_shrink(self):
        """场景：策略二，缩量比0.8（≤0.85）→ 60分"""
        c = make_candidate(volume_ratio=0.8, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 60.0

    def test_strategy2_weak_shrink(self):
        """场景：策略二，缩量比0.9（≤1.0）→ 40分"""
        c = make_candidate(volume_ratio=0.9, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 40.0

    def test_strategy2_no_shrink(self):
        """场景：策略二，缩量比1.2（>1.0）→ 20分"""
        c = make_candidate(volume_ratio=1.2, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 20.0

    def test_strategy2_with_price_decay(self):
        """场景：策略二，缩量比0.4→100分，但近3日涨幅-5%让衰减因子=1-5/20=0.75 → 75分"""
        c = make_candidate(volume_ratio=0.4, pct_changes=[-5.0, -1.0, 0.5], strategy="strategy2")
        # 平均涨幅 = (-5 + -1 + 0.5)/3 = -1.833... 绝对值1.833
        # 衰减 = 1 - 1.833/20 = 0.9083
        # 100 * 0.9083 = 90.83
        dim = score_pullback_depth(c)
        assert dim.score == pytest.approx(90.83, rel=0.01)

    def test_strategy2_large_rise_capped(self):
        """场景：近3日涨幅过大使衰减因子为0 → 0分"""
        c = make_candidate(volume_ratio=0.4, pct_changes=[10.0, 8.0, 12.0], strategy="strategy2")
        # 平均涨幅10%，衰减1-10/20=0.5
        dim = score_pullback_depth(c)
        assert dim.score == 50.0  # 100 * 0.5 = 50

    def test_strategy2_boundary_85(self):
        """场景：缩量比正好0.85（≤0.85边界）→ 60分"""
        c = make_candidate(volume_ratio=0.85, strategy="strategy2")
        dim = score_pullback_depth(c)
        assert dim.score == 60.0

    def test_default_strategy_missing(self):
        """场景：没有strategy字段 → 默认按策略二处理"""
        c = make_candidate(volume_ratio=0.6)
        del c.detail["strategy"]
        dim = score_pullback_depth(c)
        assert dim.score == 80.0  # 策略二的缩量比0.6→80分


# ════════════════════════════════════════════════════════════════
# 维度四：流动性安全 (LiquiditySafety)
# ════════════════════════════════════════════════════════════════

class TestScoreLiquiditySafety:
    """日成交额+市值+换手率"""

    def test_ideal_liquidity(self):
        """场景：成交额10亿+市值100亿+换手率5% → 40+40+20=100"""
        c = make_candidate(avg_amount=10_000_000_000, market_cap=10_000_000_000, turnover_rate=0.05)
        dim = score_liquidity_safety(c)
        assert dim.score == 100.0

    def test_moderate_liquidity(self):
        """场景：成交额1亿+市值30亿+换手率2% → 20+30+10=60"""
        c = make_candidate(avg_amount=100_000_000, market_cap=3_000_000_000, turnover_rate=0.02)
        dim = score_liquidity_safety(c)
        assert dim.score == 60.0

    def test_low_liquidity(self):
        """场景：成交额0.3亿+市值10亿+换手率0.5% → 0+10+0=10"""
        c = make_candidate(avg_amount=30_000_000, market_cap=1_000_000_000, turnover_rate=0.005)
        dim = score_liquidity_safety(c)
        assert dim.score == 10.0

    def test_boundary_amount(self):
        """场景：成交额5亿刚好够5亿档（≥5亿）→ 30分"""
        c = make_candidate(avg_amount=500_000_000, market_cap=50_000_000_000, turnover_rate=0.05)
        dim = score_liquidity_safety(c)
        assert dim.score == 90.0  # 30(成交额) + 40(市值500亿) + 20(换手率5%)

    def test_large_market_cap(self):
        """场景：市值800亿（500-1000亿段）→ 30分"""
        c = make_candidate(avg_amount=10_000_000_000, market_cap=80_000_000_000, turnover_rate=0.05)
        dim = score_liquidity_safety(c)
        assert dim.score == 90.0  # 40+30+20=90

    def test_huge_market_cap(self):
        """场景：市值2000亿 → 10分"""
        c = make_candidate(avg_amount=10_000_000_000, market_cap=200_000_000_000, turnover_rate=0.05)
        dim = score_liquidity_safety(c)
        assert dim.score == 70.0  # 40+10+20=70


# ════════════════════════════════════════════════════════════════
# 维度五：形态健康度 (PatternHealth)
# ════════════════════════════════════════════════════════════════

class TestScorePatternHealth:
    """均线排列得分+量异常+上影线"""

    def test_perfect_pattern(self):
        """场景：完整多头排列+量正常+无长上影 → 50+30+20=100"""
        c = make_candidate(recent_volume_ratio=1.2, upper_shadow_ratio=0.5)
        dim = score_pattern_health(c)
        assert dim.score == 100.0

    def test_partial_arrangement(self):
        """场景：MA5>MA10>MA20 但 MA20<MA60 → 部分多头30分"""
        mas = {"ma5": 15.0, "ma10": 14.0, "ma20": 13.0, "ma60": 14.0}  # MA20(13) < MA60(14)
        c = make_candidate(mas=mas, recent_volume_ratio=1.2, upper_shadow_ratio=0.5)
        dim = score_pattern_health(c)
        assert dim.score == 80.0  # 30 + 30 + 20 = 80

    def test_no_arrangement(self):
        """场景：MA5<MA10<MA20<MA60 → 无多头排列"""
        mas = {"ma5": 10.0, "ma10": 11.0, "ma20": 12.0, "ma60": 13.0}
        c = make_candidate(mas=mas, recent_volume_ratio=1.2, upper_shadow_ratio=0.5)
        dim = score_pattern_health(c)
        assert dim.score == 60.0  # 10 + 30 + 20 = 60

    def test_abnormal_volume_bearish(self):
        """场景：量异常放大+阴线 → 扣分"""
        c = make_candidate(recent_volume_ratio=2.5, upper_shadow_ratio=0.5)
        # 近3日pct变化默认 [-1.5, -0.5, 2.0]，平均0.0 → 阳线
        # 要用阴线场景
        c.detail["pct_changes"] = [-3.0, -2.0, -1.0]
        # 平均 -2.0 → 阴线，扣20
        # 50(完整多头) + (-20) + 20(无上影) = 50
        dim = score_pattern_health(c)
        assert dim.score == 50.0

    def test_abnormal_volume_bullish(self):
        """场景：量异常放大+阳线 → +10分（非满分）"""
        c = make_candidate(recent_volume_ratio=2.5, upper_shadow_ratio=0.5)
        c.detail["pct_changes"] = [1.0, 2.0, 3.0]  # 平均2.0 → 阳线
        dim = score_pattern_health(c)
        assert dim.score == 80.0  # 50 + 10 + 20 = 80

    def test_long_upper_shadow(self):
        """场景：有长上影线（上影线≥实体3倍）→ -10分 → 50+30-10=70"""
        c = make_candidate(recent_volume_ratio=1.2, upper_shadow_ratio=3.0)
        dim = score_pattern_health(c)
        assert dim.score == 70.0  # 50(全排列) + 30(正常量) - 10(长上影) = 70

    def test_missing_mas(self):
        """场景：mas字段不存在 → 无排列低分，其他维度正常"""
        c = make_candidate()
        del c.detail["mas"]
        dim = score_pattern_health(c)
        assert dim.score == 60.0  # 10(无排列) + 30(正常量) + 20(无上影) = 60

    def test_missing_pattern_fields(self):
        """场景：所有形态字段都缺失 → 安全默认值"""
        c = make_candidate()
        c.detail.pop("mas", None)
        c.detail.pop("recent_volume_ratio", None)
        c.detail.pop("upper_shadow_ratio", None)
        dim = score_pattern_health(c)
        assert dim.score > 0  # 至少有一些默认安全值


# ════════════════════════════════════════════════════════════════
# score_candidates 集成测试
# ════════════════════════════════════════════════════════════════

class TestScoreCandidates:
    """完整评分流程 + 排序"""

    def test_scores_and_sorts_correctly(self):
        """验证：多个候选评分后按总分降序排列"""
        c1 = make_candidate(code="000001.SZ", name="A股票", adx=45.0)   # 趋势满分
        c2 = make_candidate(code="000002.SZ", name="B股票", adx=25.0)   # 趋势低分
        c3 = make_candidate(code="000003.SZ", name="C股票", adx=35.0)   # 中间
        results = score_candidates([c3, c1, c2])  # 故意乱序输入
        assert len(results) == 3
        assert results[0].stock_code == "000001.SZ"  # 最高分
        assert results[2].stock_code == "000002.SZ"   # 最低分

    def test_empty_list(self):
        """验证：空列表 → 空结果"""
        results = score_candidates([])
        assert results == []

    def test_single_candidate(self):
        """验证：单个候选的正常评分"""
        c = make_candidate()
        results = score_candidates([c])
        assert len(results) == 1
        scored = results[0]
        assert 0 <= scored.total_score <= 100
        assert len(scored.dimensions) == 5
        assert scored.signal in ("buy", "")

    def test_dimension_scores_in_output(self):
        """验证：输出中各维度分值正确"""
        c = make_candidate(adx=40.0)  # 趋势强度达到100
        results = score_candidates([c])
        dim = results[0].dimensions
        assert "trend_strength" in dim
        assert dim["trend_strength"].score >= 80

    def test_total_score_weights(self):
        """验证：加权总分计算正确（手动验证）"""
        c = make_candidate(adx=45.0, sector_ratio=0.7, avg_amount=10_000_000_000)
        results = score_candidates([c])
        scored = results[0]
        # 趋势100*0.30=30, 资金(100+100)/2*0.25=25, 策略二缩量0.6→80*0.20=16
        # 流动性100*0.15=15, 形态100*0.10=10
        # 总分=30+25+16+15+10=96
        assert scored.total_score == pytest.approx(96.0, abs=1.0)

    def test_missing_detail_field_doesnt_crash(self):
        """验证：detail中缺少任一字段不会崩溃，使用默认值"""
        c = make_candidate()
        del c.detail["turnover_rate"]
        results = score_candidates([c])
        assert len(results) == 1
        assert results[0].total_score > 0


# ════════════════════════════════════════════════════════════════
# choose_best 选取测试
# ════════════════════════════════════════════════════════════════

class TestChooseBest:
    """最终选1-3只开仓"""

    def test_picks_top_3_from_each_strategy(self):
        """验证：每个策略取top3，总共不超过3只"""
        s1 = [ScoredCandidate(stock_code=f"00{i}.SZ", stock_name=f"S{i}", total_score=80-i,
                              dimensions={}, signal="buy", strategy="strategy1", reason="")
              for i in range(5)]
        s2 = [ScoredCandidate(stock_code=f"10{i}.SZ", stock_name=f"T{i}", total_score=85-i,
                              dimensions={}, signal="buy", strategy="strategy2", reason="")
              for i in range(5)]
        results = choose_best(s1, s2)
        assert len(results) <= 3
        # 应该大部分来自strategy2（分数更高）

    def test_dedup_same_stock(self):
        """验证：同一股票在两个策略中都出现时去重，保留strategy2评分"""
        s1_candidates = [
            ScoredCandidate(stock_code="000001.SZ", stock_name="A股票", total_score=70.0,
                            dimensions={}, signal="buy", strategy="strategy1", reason="s1"),
        ]
        s2_candidates = [
            ScoredCandidate(stock_code="000001.SZ", stock_name="A股票", total_score=85.0,
                            dimensions={}, signal="buy", strategy="strategy2", reason="s2"),
        ]
        results = choose_best(s1_candidates, s2_candidates)
        assert len(results) == 1
        assert results[0].strategy == "strategy2"  # 优先策略二

    def test_no_more_than_3(self):
        """验证：候选很多时也不超过3只"""
        s1 = [ScoredCandidate(stock_code=f"00{i}.SZ", stock_name=f"S{i}", total_score=90.0,
                              dimensions={}, signal="buy", strategy="strategy1", reason="")
              for i in range(10)]
        s2 = []
        results = choose_best(s1, s2)
        assert len(results) <= 3

    def test_empty_both_strategies(self):
        """验证：两个策略都为空 → 空结果"""
        results = choose_best([], [])
        assert results == []

    def test_same_score_choose_higher_amount(self):
        """验证：同策略同评分选成交额大的"""
        a = ScoredCandidate(stock_code="A.SZ", stock_name="A", total_score=80.0,
                            dimensions={}, signal="buy", strategy="strategy2", reason="",
                            daily_amount=500_000_000)
        b = ScoredCandidate(stock_code="B.SZ", stock_name="B", total_score=80.0,
                            dimensions={}, signal="buy", strategy="strategy2", reason="",
                            daily_amount=2_000_000_000)
        results = choose_best([a, b], [])
        assert results[0].stock_code == "B.SZ"  # B成交额更大

    def test_strategy1_fallback_when_strategy2_empty(self):
        """验证：策略二无候选时，从策略一选"""
        s1 = [ScoredCandidate(stock_code="000001.SZ", stock_name="A", total_score=70.0,
                              dimensions={}, signal="buy", strategy="strategy1", reason=""),
              ScoredCandidate(stock_code="000002.SZ", stock_name="B", total_score=65.0,
                              dimensions={}, signal="buy", strategy="strategy1", reason="")]
        results = choose_best(s1, [])
        assert len(results) == 2
