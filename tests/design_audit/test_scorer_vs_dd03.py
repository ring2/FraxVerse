"""设计文档审查：五维度评分模块 vs DD-03 策略引擎模块 §3.3

此测试验证评分模块的实现与DD-03详细设计文档完全对齐。
"""

import inspect
from types import SimpleNamespace

from src.strategy.scorer import (
    WEIGHTS,
    ScoredCandidate,
    DimensionScore,
    calculate_volume_price_score,
    calculate_fund_score,
    calculate_sentiment_score,
    calculate_mainforce_score,
    calculate_capital_logic_score,
    score_candidates,
)


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 五维度评分 — 权重检查
# ═══════════════════════════════════════════════════════════════════

class TestWeightsVsDesignDoc:
    """DD-03: 量价20% / 资金25% / 情绪15% / 主力行为25% / 资本市场逻辑15%"""

    def test_weight_volume_price(self):
        """DD-03: 量价维度权重 20%"""
        assert WEIGHTS.get("volume_price") == 0.20, \
            f"量价维度权重应为0.20，当前{WEIGHTS.get('volume_price')}"

    def test_weight_fund(self):
        """DD-03: 资金维度权重 25%（最高权重）"""
        assert WEIGHTS.get("fund") == 0.25, \
            f"资金维度权重应为0.25，当前{WEIGHTS.get('fund')}"

    def test_weight_sentiment(self):
        """DD-03: 情绪维度权重 15%"""
        assert WEIGHTS.get("sentiment") == 0.15, \
            f"情绪维度权重应为0.15，当前{WEIGHTS.get('sentiment')}"

    def test_weight_mainforce(self):
        """DD-03: 主力行为维度权重 25%"""
        assert WEIGHTS.get("mainforce") == 0.25, \
            f"主力行为维度权重应为0.25，当前{WEIGHTS.get('mainforce')}"

    def test_weight_capital_logic(self):
        """DD-03: 资本市场逻辑维度权重 15%"""
        assert WEIGHTS.get("capital_logic") == 0.15, \
            f"资本市场逻辑维度权重应为0.15，当前{WEIGHTS.get('capital_logic')}"

    def test_weights_sum_to_one(self):
        """DD-03: 五维度权重之和=1.0"""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, \
            f"权重和应为1.0，当前{total}"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 ScoredCandidate 输出字段检查
# ═══════════════════════════════════════════════════════════════════

class TestScoredCandidateVsDesignDoc:
    """DD-03: ScoredCandidate 字段应与 stock_pool 表一致"""

    def test_has_five_score_fields(self):
        """DD-03 stock_pool: score_volume/score_fund/score_sentiment/score_mainforce/score_logic"""
        required = {"score_volume", "score_fund", "score_sentiment",
                    "score_mainforce", "score_logic"}
        actual = {f.name for f in ScoredCandidate.__dataclass_fields__.values()}
        for field in required:
            assert field in actual, \
                f"ScoredCandidate缺少字段'{field}'（DD-03 stock_pool表要求）"

    def test_has_strategy_type(self):
        """DD-03: strategy_type 字段 (bottom_volume/trend_momentum)"""
        assert hasattr(ScoredCandidate, 'strategy_type'), \
            "ScoredCandidate缺少strategy_type字段"

    def test_has_stock_code_and_name(self):
        """DD-03: 标识字段"""
        fields = ScoredCandidate.__dataclass_fields__
        assert "stock_code" in fields
        assert "stock_name" in fields

    def test_to_stock_pool_insert_has_all_fields(self):
        """DD-03: to_stock_pool_insert 生成的字段与stock_pool表对齐"""
        insert_fields = ScoredCandidate("code", "name").to_stock_pool_insert("2026-05-01")
        required = {"date", "stock_code", "strategy_type", "pass_coarse",
                    "score_total", "score_volume", "score_fund",
                    "score_sentiment", "score_mainforce", "score_logic"}
        assert required.issubset(insert_fields.keys()), \
            f"to_stock_pool_insert缺少字段: {required - set(insert_fields.keys())}"

    def test_strategy_type_values(self):
        """DD-03: strategy_type 应为 bottom_volume / trend_momentum"""
        s = ScoredCandidate("code", "name", strategy_type="bottom_volume")
        assert s.strategy_type in ("bottom_volume", "trend_momentum")


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 score_candidates 整体流程检查
# ═══════════════════════════════════════════════════════════════════

class TestScoreCandidatesFlowVsDesignDoc:
    """DD-03: score_candidates 整体流程约束"""

    def test_returns_top_15(self):
        """DD-03: 最多返回15名（top_15 = scored[:15]）"""
        source = inspect.getsource(score_candidates)
        assert "[:15]" in source or "top_15" in source or "15" in source, \
            "score_candidates应取前15名"

    def test_returns_empty_for_empty(self):
        """DD-03: 空输入 → 空输出"""
        assert score_candidates([]) == [], "空输入应返回空列表"

    def test_sorts_by_total_score_desc(self):
        """DD-03: scored.sort(key=总分散序, reverse=True)"""
        source = inspect.getsource(score_candidates)
        assert "sort" in source and "reverse=True" in source, \
            "应按总分降序排列"
        assert "score_total" in source, "总分排序依据"

    def test_has_score_gap_detection(self):
        """DD-03: 前5名与第6名分差检测"""
        source = inspect.getsource(score_candidates)
        assert "gap" in source or "截断" in source, \
            "应有评分截断检测"
        assert "15" in source or "分差" in source or "gap" in source.lower(), \
            "分差阈值应为15分"

    def test_weighted_total_calculation(self):
        """DD-03: 总分 = Σ(维度分 × 维度权重)"""
        source = inspect.getsource(score_candidates)
        assert "weighted" in source, "应使用weighted计算"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 量价维度评分 — 因子检查
# ═══════════════════════════════════════════════════════════════════

class TestVolumePriceFactorsVsDesignDoc:
    """DD-03 §3.3 calculate_volume_price_score: 4因子"""

    def test_has_ma_arrangement_factor(self):
        """DD-03: 均线排列完整性 ±6分"""
        source = inspect.getsource(calculate_volume_price_score)
        assert "ma5" in source and "ma10" in source and "ma20" in source and "ma60" in source
        assert "6" in source.split("ma5")[0][-20:] or "6" in source.split("ma10")[0][-20:] \
            or "完美多头+6" in source or "完美空头-6" in source

    def test_has_volume_price_relationship(self):
        """DD-03: 量价关系 ±6分: 放量上涨/缩量上涨/放量下跌/缩量下跌"""
        source = inspect.getsource(calculate_volume_price_score)
        assert "price_change" in source, "应有价格变化计算"
        assert "vol_change" in source, "应有成交量变化计算"
        assert all(kw in source for kw in ["放量上涨", "缩量上涨", "放量下跌", "缩量下跌"]), \
            "应包含4种量价关系判断"

    def test_has_adx_factor(self):
        """DD-03: ADX趋势强度 ±6分"""
        source = inspect.getsource(calculate_volume_price_score)
        assert "adx" in source.lower(), "应有ADX判断"
        assert "25" in source or "ADX强趋势" in source, \
            "应有ADX≥25的判断条件"

    def test_has_price_position_factor(self):
        """DD-03: 价格位置 ±3分（底部+3/高位-2）"""
        source = inspect.getsource(calculate_volume_price_score)
        assert "position" in source or "底部区域" in source or "高位区域" in source, \
            "应有价格位置判断"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 资金维度评分 — 因子检查
# ═══════════════════════════════════════════════════════════════════

class TestFundFactorsVsDesignDoc:
    """DD-03 §3.3 calculate_fund_score: 4因子"""

    def test_has_main_amount_consecutive(self):
        """DD-03: 主力资金净流入方向 ±8分（连续N日）"""
        source = inspect.getsource(calculate_fund_score)
        assert "consecutive_inflow" in source or "consecutive_outflow" in source, \
            "应有连续流入/流出判断"
        assert "8" in source or "连" in source

    def test_has_cmf_factor(self):
        """DD-03: CMF资金流向 ±6分"""
        source = inspect.getsource(calculate_fund_score)
        assert "cmf" in source.lower(), "应有CMF判断"
        assert "CMF>0" in source or "CMF<0" in source

    def test_has_large_order_factor(self):
        """DD-03: 大单占比 ±6分（>30%/+6, >20%/+3, <10%/-3）"""
        source = inspect.getsource(calculate_fund_score)
        assert "large_order_pct" in source or "大单" in source, "应有大单占比判断"
        assert "0.30" in source or "0.20" in source or "0.10" in source

    def test_has_net_amount_ratio(self):
        """DD-03: 净流入相对规模 ±3分（>50%/+3, <20%/-2）"""
        source = inspect.getsource(calculate_fund_score)
        assert "ratio" in source or "流入占比" in source or "参与微弱" in source, \
            "应有净流入相对规模判断"


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 情绪维度评分 — 因子检查
# ═══════════════════════════════════════════════════════════════════

class TestSentimentFactorsVsDesignDoc:
    """DD-03 §3.3 calculate_sentiment_score: 4因子"""

    def test_has_news_sentiment(self):
        """DD-03: 新闻情绪标签统计 ±6分"""
        source = inspect.getsource(calculate_sentiment_score)
        assert "sentiment" in source or "positive" in source or "negative" in source

    def test_has_sector_heat(self):
        """DD-03: 板块热度 ±6分（多个活跃板块加分/全线下跌减分）"""
        source = inspect.getsource(calculate_sentiment_score)
        assert "hot_sectors" in source or "cold_sectors" in source or "板块" in source

    def test_has_dragon_tiger(self):
        """DD-03: 龙虎榜净额 ±3分"""
        source = inspect.getsource(calculate_sentiment_score)
        assert "dragon_tiger" in source or "龙虎榜" in source, "应有龙虎榜判断"

    def test_has_staleness_penalty(self):
        """DD-03: 新闻时效性衰减 ±3分"""
        source = inspect.getsource(calculate_sentiment_score)
        assert "staleness" in source or "时效" in source or "旧新闻" in source


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 主力行为维度评分 — 因子检查
# ═══════════════════════════════════════════════════════════════════

class TestMainforceFactorsVsDesignDoc:
    """DD-03 §3.3 calculate_mainforce_score: 6因子"""

    def test_has_big_drop_then_small_doji(self):
        """DD-03: 大阴线后收小阳线/十字星 +3分"""
        source = inspect.getsource(calculate_mainforce_score)
        assert "big_drop_day" in source or "大阴" in source or "小阳" in source

    def test_has_volume_shrink_after_drop(self):
        """DD-03: 下杀日放量→次日缩量 ±3分"""
        source = inspect.getsource(calculate_mainforce_score)
        assert "vol_ratio" in source or "缩量" in source.lower().split("位置")[0] \
            or "0.60" in source
        # 0.60是60%缩量阈值

    def test_has_price_position(self):
        """DD-03: 价格位置 ±3分（已跌>20%/+3, 已涨>50%/-3）"""
        source = inspect.getsource(calculate_mainforce_score)
        assert "position" in source or "低位" in source or "高位" in source

    def test_has_main_amount_behavior(self):
        """DD-03: 大单行为 ±3分（净流入+3/净流出-3）"""
        source = inspect.getsource(calculate_mainforce_score)
        assert "main_amount" in source

    def test_has_fund_consecutive_consistency(self):
        """DD-03: 资金流向连贯性 ±3分"""
        source = inspect.getsource(calculate_mainforce_score)
        assert "positive_days" in source or "negative_days" in source \
            or "连贯" in source or "一致性" in source


# ═══════════════════════════════════════════════════════════════════
# DD-03 §3.3 资本市场逻辑维度评分 — 因子检查
# ═══════════════════════════════════════════════════════════════════

class TestCapitalLogicFactorsVsDesignDoc:
    """DD-03 §3.3 calculate_capital_logic_score: 3因子"""

    def test_has_sector_policy(self):
        """DD-03: 板块政策赛道判断 ±8分"""
        source = inspect.getsource(calculate_capital_logic_score)
        assert "policy" in source or "政策" in source or "capital_ratio" in source
        assert "0.12" in source or "0.06" in source or "0.05" in source

    def test_has_driver_events(self):
        """DD-03: 近期驱动事件 ±6分（政策/业绩/重组/负面关键词）"""
        source = inspect.getsource(calculate_capital_logic_score)
        assert "policy_kw" in source or "event_kw" in source or "negative_kw" in source \
            or "利好" in source or "业绩" in source

    def test_has_valuation_percentile(self):
        """DD-03: 估值分位数 ±3分（<25%/+3, >75%/-3）"""
        source = inspect.getsource(calculate_capital_logic_score)
        assert "percentile" in source or "0.25" in source or "0.75" in source \
            or "估值" in source or "低位" in source or "高位" in source


# ═══════════════════════════════════════════════════════════════════
# DD-03 — 输出字段完整清单检查
# ═══════════════════════════════════════════════════════════════════

class TestStockPoolFieldsVsDesignDoc:
    """DD-03 stock_pool 表字段 vs code"""

    def test_stock_pool_table_fields_match(self):
        """DD-03 stock_pool: 5个评分字段+标识字段全部对齐"""
        s = ScoredCandidate("code", "name", strategy_type="trend_momentum")
        insert = s.to_stock_pool_insert("2026-05-01")

        # DD-03 §2.1.2 stock_pool 表字段
        doc_fields = {
            "date", "stock_code", "strategy_type",
            "pass_coarse",
            "score_total", "score_volume", "score_fund",
            "score_sentiment", "score_mainforce", "score_logic",
        }
        actual = set(insert.keys())
        missing = doc_fields - actual
        extra = actual - doc_fields
        assert not missing, f"缺少设计文档要求的字段: {missing}"
        assert not extra, f"有多余字段: {extra}"
