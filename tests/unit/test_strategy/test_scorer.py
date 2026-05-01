"""测试五维度评分模块（按DD-03详细设计文档）

P0-4.1: 五维度评分 — 量价20% / 资金25% / 情绪15% / 主力行为25% / 逻辑15%

测试覆盖：
1. 量价维度：均线排列、量价关系、ADX、价格位置
2. 资金维度：主力连流入、CMF、大单占比、净流入规模
3. 情绪维度：新闻情绪、板块热度、龙虎榜、时效性
4. 主力行为维度：大阴线+小阳线、下杀缩量、价格位置、大单行为、资金连贯性
5. 逻辑维度：板块政策、驱动事件、估值分位数
6. 集成评分：结果排序、取前15、评分截断、空列表
"""

from types import SimpleNamespace

from src.strategy.scorer import (
    calculate_capital_logic_score,
    calculate_fund_score,
    calculate_mainforce_score,
    calculate_sentiment_score,
    calculate_volume_price_score,
    score_candidates,
)

# ── 辅助函数 ────────────────────────────────────────────────────

def make_kline(
    close: float = 10.0,
    open_p: float = 10.0,
    high: float = 10.5,
    low: float = 9.5,
    volume: float = 1_000_000,
    amount: float = 10_000_000,
    ma5: float | None = 10.0,
    ma10: float | None = 9.5,
    ma20: float | None = 9.0,
    ma60: float | None = 8.5,
    adx: float | None = 30.0,
    trade_date: str = "2026-05-01",
) -> dict:
    return {
        "trade_date": trade_date,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "adx": adx,
    }


def make_fund(
    main_amount: float | None = 50_000_000,
    net_amount: float | None = 100_000_000,
    cmf: float | None = 0.05,
    large_order_pct: float | None = 0.25,
    trade_date: str = "2026-05-01",
) -> dict:
    return {
        "trade_date": trade_date,
        "main_amount": main_amount,
        "net_amount": net_amount,
        "cmf": cmf,
        "large_order_pct": large_order_pct,
    }


def make_news(
    title: str = "公司业绩预增，政策利好",
    sentiment: str | None = "positive",
    category: str = "finance",
    is_hot: bool = False,
    trade_date: str = "2026-05-01",
    hot_sectors: int = 2,
    cold_sectors: int = 3,
) -> dict:
    return {
        "title": title,
        "sentiment": sentiment,
        "category": category,
        "is_hot": is_hot,
        "trade_date": trade_date,
        "_hot_sectors": hot_sectors,
        "_cold_sectors": cold_sectors,
        "_staleness": 0,
    }


def make_strategy_candidate(code: str = "000001.SZ", name: str = "测试股票"):
    """创建带detail的候选对象"""
    c = SimpleNamespace()
    c.stock_code = code
    c.stock_name = name
    c.reason = "测试"
    c.daily_amount = 2_000_000_000
    c.detail = {
        "strategy": "trend_momentum",
        "_sectors": [
            {"sector_name": "半导体", "capital_ratio": 0.15, "change_pct": 2.5},
        ],
    }
    return c


# ════════════════════════════════════════════════════════════════
# 量价维度 VolumePrice (20%)
# ════════════════════════════════════════════════════════════════

class TestVolumePriceScore:

    def test_perfect_bullish(self):
        """场景：完美多头排列+放量上涨+ADX强趋势 → 68分"""
        klines = [
            make_kline(close=10.0, open_p=9.8, volume=1_500_000,
                       ma5=10.0, ma10=9.5, ma20=9.0, ma60=8.5, adx=35.0),
            make_kline(close=9.5, open_p=9.6, volume=1_000_000, trade_date="2026-04-30",
                       ma5=9.5, ma10=9.3, ma20=9.0, ma60=8.5, adx=30.0),
            make_kline(close=9.0, open_p=9.2, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=8.5, open_p=8.5, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=8.5, open_p=8.5, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 68.0  # 50 + 6 + 6 + 6

    def test_volume_price_rise(self):
        """场景：放量上涨 (+6) + ADX(+6) = 62"""
        klines = [
            make_kline(close=10.0, open_p=9.8, volume=2_000_000, adx=30.0, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=9.0, open_p=9.0, volume=1_000_000, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=8.5, open_p=8.5, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=8.5, open_p=8.5, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=8.5, open_p=8.5, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 62.0  # 50 + 6(放量上涨) + 6(ADX>25)

    def test_volume_drop_panic(self):
        """场景：放量下跌 (-6) + ADX(+6) = 50"""
        klines = [
            make_kline(close=8.0, open_p=9.5, volume=2_000_000, adx=30.0, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, open_p=10.0, volume=1_000_000, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 50.0  # 50 - 6 + 6

    def test_volume_shrink_rise(self):
        """场景：缩量上涨 (-3) + ADX(+6) = 53"""
        klines = [
            make_kline(close=10.2, open_p=10.0, volume=500_000, adx=30.0, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, open_p=10.0, volume=1_000_000, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=9.5, open_p=9.5, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=9.5, open_p=9.5, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=9.5, open_p=9.5, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 53.0  # 50 - 3 + 6

    def test_volume_shrink_drop_healthy(self):
        """场景：缩量下跌+ADX强趋势 (+3+6) = 59"""
        klines = [
            make_kline(close=9.8, open_p=10.0, volume=500_000, adx=30.0, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, open_p=10.0, volume=1_000_000, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=10.0, open_p=10.0, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 59.0  # 50 + 3 + 6

    def test_adx_weak_trend(self):
        """场景：ADX<20 无趋势 (-3)"""
        klines = [
            make_kline(close=10.0, adx=15.0, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, adx=14.0, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=10.0, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=10.0, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=10.0, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 47.0  # 50 - 3

    def test_price_position_bottom(self):
        """场景：价格在60日底部区域 (+3)"""
        klines = []
        for i in range(60):
            c = 10.0 - i * 0.05 if i < 59 else 7.0
            klines.append(make_kline(close=c, trade_date=f"2026-03-{i+1:02d}"))
        klines[0] = make_kline(close=7.5, adx=30.0, trade_date="2026-05-01")
        dim = calculate_volume_price_score(klines)
        assert dim.score > 53

    def test_price_position_high(self):
        """场景：价格在60日高位区域 (-2) + ADX(+6) = 54"""
        klines = []
        for i in range(60):
            c = 10.0 + i * 0.05 if i < 59 else 13.0
            klines.append(make_kline(close=c, ma5=None, ma10=None, ma20=None, ma60=None,
                                     trade_date=f"2026-03-{i+1:02d}"))
        klines[0] = make_kline(close=13.0, adx=30.0, ma5=None, ma10=None, ma20=None, ma60=None,
                               trade_date="2026-05-01")
        dim = calculate_volume_price_score(klines)
        assert dim.score == 54.0  # 50 + 6 - 2

    def test_missing_adx_no_change(self):
        """场景：无ADX数据 → 不扣分"""
        klines = [
            make_kline(close=10.0, adx=None, ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=9.0, volume=1_000_000, trade_date="2026-04-30", ma5=None, ma10=None, ma20=None, ma60=None),
            make_kline(close=9.0, volume=800_000, trade_date="2026-04-29"),
            make_kline(close=9.0, volume=800_000, trade_date="2026-04-28"),
            make_kline(close=9.0, volume=800_000, trade_date="2026-04-27"),
        ]
        dim = calculate_volume_price_score(klines)
        assert dim.score == 50.0


# ════════════════════════════════════════════════════════════════
# 资金维度 Fund (25%)
# ════════════════════════════════════════════════════════════════

class TestFundScore:

    def test_strong_inflow(self):
        """场景：连续3日主力净流入+CMF>0+大单>30% → 70分"""
        fund_flow = [
            make_fund(main_amount=50_000_000, cmf=0.05, large_order_pct=0.35),
            make_fund(main_amount=30_000_000, cmf=0.03, trade_date="2026-04-30"),
            make_fund(main_amount=20_000_000, cmf=0.02, trade_date="2026-04-29"),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score == 70.0  # 50+8+3+3+6

    def test_strong_outflow(self):
        """场景：连续3日主力净流出+CMF<0+大单<10% → 低分"""
        fund_flow = [
            make_fund(main_amount=-30_000_000, cmf=-0.05, large_order_pct=0.08),
            make_fund(main_amount=-20_000_000, cmf=-0.03, trade_date="2026-04-30"),
            make_fund(main_amount=-10_000_000, cmf=-0.02, trade_date="2026-04-29"),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score < 40

    def test_moderate_inflow(self):
        """场景：单日主力净流入+CMF>0+大单22%+参与弱 → 56分"""
        fund_flow = [
            make_fund(main_amount=10_000_000, cmf=0.02, large_order_pct=0.22),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score == 56.0  # 50+2+3+3-2

    def test_no_fund_flow(self):
        """场景：无资金流数据 → 基准50"""
        dim = calculate_fund_score([])
        assert dim.score == 50.0

    def test_net_amount_ratio_dominant(self):
        """场景：主力净流入占主导 (>50%) → 单日+2+CMF+3+占比+3 = 58"""
        fund_flow = [
            make_fund(main_amount=60_000_000, net_amount=100_000_000, large_order_pct=0.15),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score == 58.0  # 50+2+3+3

    def test_mixed_inflow_outflow_break(self):
        """场景：混合流入流出 → 单日流入+2, 流出-2, CMF>0+3, 大单+3 = 56"""
        fund_flow = [
            make_fund(main_amount=50_000_000),
            make_fund(main_amount=-10_000_000, trade_date="2026-04-30"),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score == 56.0  # 50+2-2+3+3

    def test_consecutive_inflow_exactly_2(self):
        """场景：恰好2日连续流入 → +5 + CMF(0) + 大单0%-3 + 参与弱-2 = 50"""
        fund_flow = [
            make_fund(main_amount=10_000_000, cmf=0.0, large_order_pct=0.0),
            make_fund(main_amount=20_000_000, cmf=0.0, large_order_pct=0.0, trade_date="2026-04-30"),
        ]
        dim = calculate_fund_score(fund_flow)
        assert dim.score == 50.0  # 50+5-3-2


# ════════════════════════════════════════════════════════════════
# 情绪维度 Sentiment (15%)
# ════════════════════════════════════════════════════════════════

class TestSentimentScore:

    def test_positive_sentiment(self):
        """场景：正面新闻+多板块活跃 → 高分"""
        news = [
            make_news(sentiment="positive", hot_sectors=3),
            make_news(sentiment="positive"),
        ]
        dim = calculate_sentiment_score(news, "2026-05-01")
        assert dim.score > 55

    def test_negative_sentiment(self):
        """场景：负面新闻+多板块下跌 → 低分"""
        news = [
            make_news(title="公司违规被处罚", sentiment="negative", cold_sectors=12),
        ]
        dim = calculate_sentiment_score(news, "2026-05-01")
        assert dim.score < 45

    def test_dragon_tiger_boost(self):
        """场景：龙虎榜机构买入 → +3 (正面+6 + 板块+3 + 龙虎榜+3 = 62)"""
        news = [
            make_news(title="龙虎榜机构买入", sentiment="positive", hot_sectors=1),
        ]
        dim = calculate_sentiment_score(news, "2026-05-01")
        assert dim.score == 62.0  # 50+6+3+3

    def test_empty_news(self):
        """场景：无新闻数据 → 基准50"""
        dim = calculate_sentiment_score([], "2026-05-01")
        assert dim.score == 50.0

    def test_stale_news_penalty(self):
        """场景：新闻时效性差+正面+2板块 → 56分"""
        news = [
            make_news(sentiment="positive"),
        ]
        news[0]["_staleness"] = 3
        dim = calculate_sentiment_score(news, "2026-05-01")
        assert dim.score == 56.0  # 50+6+3-3


# ════════════════════════════════════════════════════════════════
# 主力行为维度 Mainforce (25%)
# ════════════════════════════════════════════════════════════════

class TestMainforceScore:

    def test_hard_wash_pattern(self):
        """场景：大阴线→小阳线+缩量+净流入+连贯性 → 56分"""
        klines = [
            make_kline(close=10.5, open_p=10.2, volume=400_000, trade_date="2026-05-01"),
            make_kline(close=9.0, open_p=10.0, volume=1_000_000, trade_date="2026-04-30"),
            make_kline(close=10.0, open_p=9.8, volume=800_000, trade_date="2026-04-29"),
        ]
        for i in range(57):
            c = 10.0 - i * 0.05
            klines.append(make_kline(close=c, trade_date=f"2026-03-{i+1:02d}"))
        fund_flow = [
            make_fund(main_amount=30_000_000, cmf=0.05),
            make_fund(main_amount=20_000_000, trade_date="2026-04-30"),
            make_fund(main_amount=10_000_000, trade_date="2026-04-29"),
        ]
        dim = calculate_mainforce_score(klines, fund_flow)
        assert dim.score == 56.0  # 50+3+3-3+3+3=59->56(高位-3)

    def test_distribution_pattern(self):
        """场景：持续放量+高位+净流出 → 低分"""
        klines = [
            make_kline(close=13.0, open_p=12.8, volume=1_200_000, trade_date="2026-05-01"),
            make_kline(close=12.0, open_p=13.0, volume=1_000_000, trade_date="2026-04-30"),
            make_kline(close=13.0, open_p=12.5, volume=600_000, trade_date="2026-04-29"),
        ]
        for i in range(57):
            c = 7.0 + i * 0.1
            klines.append(make_kline(close=c, trade_date=f"2026-03-{i+1:02d}"))
        fund_flow = [
            make_fund(main_amount=-30_000_000, cmf=-0.05),
            make_fund(main_amount=-20_000_000, trade_date="2026-04-30"),
        ]
        dim = calculate_mainforce_score(klines, fund_flow)
        assert dim.score < 45

    def test_no_big_drop(self):
        """场景：无大阴线 → 保持基准"""
        klines = [
            make_kline(close=10.0, open_p=9.8, volume=500_000),
            make_kline(close=9.8, open_p=9.6, volume=600_000, trade_date="2026-04-30"),
            make_kline(close=9.5, open_p=9.4, volume=700_000, trade_date="2026-04-29"),
        ]
        dim = calculate_mainforce_score(klines, [])
        assert dim.score == 50.0

    def test_fund_consecutive_negative(self):
        """场景：连续2日主力净流出 → -3"""
        klines = [
            make_kline(close=10.0, open_p=9.8),
            make_kline(close=9.8, open_p=9.6, trade_date="2026-04-30"),
            make_kline(close=9.5, open_p=9.4, trade_date="2026-04-29"),
        ]
        fund_flow = [
            make_fund(main_amount=-10_000_000, cmf=0.0),
            make_fund(main_amount=-5_000_000, cmf=0.0, trade_date="2026-04-30"),
            make_fund(main_amount=10_000_000, cmf=0.0, trade_date="2026-04-29"),
        ]
        dim = calculate_mainforce_score(klines, fund_flow)
        assert dim.score <= 47


# ════════════════════════════════════════════════════════════════
# 资本市场逻辑维度 CapitalLogic (15%)
# ════════════════════════════════════════════════════════════════

class TestCapitalLogicScore:

    def test_policy_tailwind(self):
        """场景：板块集中度高+政策利好+估值低位 → 高分"""
        candidate = {"_sectors": [{"capital_ratio": 0.15, "change_pct": 2.5}], "strategy": "trend_momentum"}
        news = [
            make_news(title="政策利好扶持，补贴力度超预期"),
            make_news(title="板块发展规划出台"),
        ]
        klines = []
        for i in range(60):
            klines.append(make_kline(close=7.0 + i * 0.05, trade_date=f"2026-03-{i+1:02d}"))
        klines[0] = make_kline(close=7.5, trade_date="2026-05-01")
        dim = calculate_capital_logic_score(candidate, news, klines)
        assert dim.score > 60

    def test_negative_event(self):
        """场景：处罚+退市风险 → -6 = 44分"""
        candidate = {"_sectors": [{"capital_ratio": 0.03, "change_pct": -1.0}], "strategy": "trend_momentum"}
        news = [
            make_news(title="公司违规处罚，面临退市风险"),
        ]
        dim = calculate_capital_logic_score(candidate, news, [])
        assert dim.score == 44.0  # 50-6

    def test_event_driver_boost(self):
        """场景：2条事件驱动 → +4 = 54分"""
        candidate = {"_sectors": [], "strategy": "trend_momentum"}
        news = [
            make_news(title="公司业绩预增超100%"),
            make_news(title="子公司中标重大合同"),
        ]
        dim = calculate_capital_logic_score(candidate, news, [])
        assert dim.score == 54.0  # 50+4

    def test_valuation_high_penalty(self):
        """场景：价格在120日高位 → -3 = 47分"""
        candidate = {"_sectors": [], "strategy": "trend_momentum"}
        klines = []
        for i in range(120):
            klines.append(make_kline(close=10.0 + i * 0.05, trade_date=f"2026-01-{(i%30)+1:02d}"))
        klines[0] = make_kline(close=15.0, trade_date="2026-05-01")
        dim = calculate_capital_logic_score(candidate, [], klines)
        assert dim.score == 47.0

    def test_sectors_missing(self):
        """场景：无板块数据 → 基准50"""
        candidate = {"_sectors": [], "strategy": "trend_momentum"}
        dim = calculate_capital_logic_score(candidate, [], [])
        assert dim.score == 50.0


# ════════════════════════════════════════════════════════════════
# 集成测试
# ════════════════════════════════════════════════════════════════

class TestScoreCandidates:

    def test_scores_all_five_dimensions(self):
        """验证：每个候选标的获得5个维度分"""
        candidates = [make_strategy_candidate("000001.SZ", "A股票")]
        klines_map = {"000001.SZ": [make_kline(adx=35.0)]}
        fm = {"000001.SZ": [make_fund()]}
        nm = {"000001.SZ": [make_news()]}
        results = score_candidates(candidates, klines_map=klines_map,
                                   fund_flow_map=fm, news_map=nm)
        assert len(results) == 1
        s = results[0]
        assert all(getattr(s, f) > 0 for f in
                   ["score_volume", "score_fund", "score_sentiment",
                    "score_mainforce", "score_logic"])

    def test_weighted_total_correct(self):
        """验证：加权总分 = 各维度分×权重的和"""
        candidates = [make_strategy_candidate("000001.SZ", "A股票")]
        km = {"000001.SZ": [make_kline()]}
        fm = {"000001.SZ": [make_fund()]}
        nm = {"000001.SZ": [make_news()]}
        results = score_candidates(candidates, klines_map=km,
                                   fund_flow_map=fm, news_map=nm)
        s = results[0]
        expected = (
            s.score_volume * 0.20 + s.score_fund * 0.25 +
            s.score_sentiment * 0.15 + s.score_mainforce * 0.25 +
            s.score_logic * 0.15
        )
        assert abs(s.score_total - round(expected, 2)) < 0.01

    def test_sorts_by_total_score_desc(self):
        """验证：按总分降序排列"""
        c1 = make_strategy_candidate("000001.SZ", "A高分")
        c2 = make_strategy_candidate("000002.SZ", "B中分")
        c3 = make_strategy_candidate("000003.SZ", "C低分")
        km = {
            "000001.SZ": [make_kline(close=10.0, adx=45.0)],
            "000002.SZ": [make_kline(close=10.0, adx=25.0)],
            "000003.SZ": [make_kline(close=10.0, adx=10.0)],
        }
        fm = {
            "000001.SZ": [make_fund(main_amount=50_000_000, cmf=0.05, large_order_pct=0.45)],
            "000002.SZ": [make_fund(main_amount=10_000_000, cmf=0.0, large_order_pct=0.15)],
            "000003.SZ": [make_fund(main_amount=-50_000_000, cmf=-0.05, large_order_pct=0.05)],
        }
        results = score_candidates([c2, c3, c1], klines_map=km, fund_flow_map=fm)
        assert len(results) == 3
        assert results[0].stock_code == "000001.SZ"
        assert results[2].stock_code == "000003.SZ"

    def test_top_15_limit(self):
        """验证：候选超过15只时只取前15"""
        candidates = [make_strategy_candidate(f"00{i:02d}.SZ") for i in range(20)]
        results = score_candidates(candidates)
        assert len(results) <= 15

    def test_empty(self):
        """验证：空列表 → 空结果"""
        assert score_candidates([]) == []

    def test_score_gap_detection(self):
        """验证：前5与第6名分差≥15分时触发截断检测"""
        candidates = [make_strategy_candidate(f"00{i:02d}.SZ", f"S{i}")
                      for i in range(10)]
        km = {}
        fm = {}
        for i in range(10):
            code = f"00{i:02d}.SZ"
            if i < 5:
                km[code] = [make_kline(close=10.0, adx=45.0)]
                fm[code] = [make_fund(main_amount=50_000_000, cmf=0.05, large_order_pct=0.45)]
            else:
                km[code] = [make_kline(close=5.0, adx=5.0)]
                fm[code] = [make_fund(main_amount=-50_000_000, cmf=-0.05, large_order_pct=0.05)]
        results = score_candidates(candidates, klines_map=km, fund_flow_map=fm)
        assert len(results) == 10
        assert results[4].score_total > results[5].score_total
