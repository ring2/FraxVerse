"""五维度评分模块

P0-4.1: 对粗筛候选标的进行五维度评分、排序、入股票池

五维度（权重）:
1. 量价维度      (20%) — 均线排列完整性、量价关系、ADX趋势强度、价格位置
2. 资金维度      (25%) — 主力资金净流入方向、CMF资金流向、大单占比、净流入相对规模
3. 情绪维度      (15%) — 新闻情绪、板块热度（P0简化版，后续Agent增强）
4. 主力行为维度  (25%) — 6因子洗盘/出货模式识别
5. 资本市场逻辑  (15%) — 板块政策赛道、驱动事件、估值分位数（P0简化版）

评分输出:
- 加权总分 0-100
- 取前15名入股票池
- 评分截断检测（前5与第6名分差≥15分时标记）
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 评分权重（设计文档固定） ──────────────────────────────────────

WEIGHTS: dict[str, float] = {
    "volume_price": 0.20,      # 量价维度
    "fund": 0.25,              # 资金维度（最高权重）
    "sentiment": 0.15,         # 情绪维度
    "mainforce": 0.25,         # 主力行为维度
    "capital_logic": 0.15,     # 资本市场逻辑维度
}


# ── 数据类 ────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    name: str
    score: float      # 0-100
    weight: float     # 固定权重
    detail: str = ""

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class ScoredCandidate:
    stock_code: str
    stock_name: str
    strategy_type: str = ""          # bottom_volume / trend_momentum
    score_total: float = 0.0
    score_volume: float = 0.0        # 量价维度
    score_fund: float = 0.0          # 资金维度
    score_sentiment: float = 0.0     # 情绪维度
    score_mainforce: float = 0.0     # 主力行为维度
    score_logic: float = 0.0         # 资本市场逻辑维度
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    reason: str = ""

    def to_stock_pool_insert(self, trade_date: str) -> dict:
        """生成入库到 stock_pool 的字段字典"""
        return {
            "date": trade_date,
            "stock_code": self.stock_code,
            "strategy_type": self.strategy_type,
            "pass_coarse": True,
            "score_total": self.score_total,
            "score_volume": self.score_volume,
            "score_fund": self.score_fund,
            "score_sentiment": self.score_sentiment,
            "score_mainforce": self.score_mainforce,
            "score_logic": self.score_logic,
        }


# ════════════════════════════════════════════════════════════════
# 维度一：量价维度 VolumePrice (20%)
#   均线排列完整性 ±6 | 量价关系 ±6 | ADX趋势强度 ±6 | 价格位置 ±3
# ════════════════════════════════════════════════════════════════

def calculate_volume_price_score(klines: list[dict]) -> DimensionScore:
    """量价维度评分 — 基准50，±21分范围，上限100下限0"""
    score = 50.0
    details: list[str] = []

    if len(klines) < 5:
        return DimensionScore("volume_price", score, WEIGHTS["volume_price"], "K线不足5根")

    latest = klines[0]

    # 因子1：均线排列完整性（±6分）
    if all(latest.get(k) is not None for k in ("ma5", "ma10", "ma20", "ma60")):
        mas = (latest["ma5"], latest["ma10"], latest["ma20"], latest["ma60"])
        if mas[0] > mas[1] > mas[2] > mas[3]:
            score += 6
            details.append("完美多头+6")
        elif mas[0] < mas[1] < mas[2] < mas[3]:
            score -= 6
            details.append("完美空头-6")
        else:
            pairs = [(mas[0], mas[1]), (mas[1], mas[2]), (mas[2], mas[3])]
            bullish_pairs = sum(1 for a, b in pairs if a > b)
            adj = (bullish_pairs - 1.5) * 2  # 0对=-3, 1对=-1, 2对=+1, 3对=+3
            score += adj
            details.append(f"部分排列{bullish_pairs}/3对{adj:+}")

    # 因子2：量价关系（±6分）
    if len(klines) >= 2:
        prev = klines[1]
        price_change = (latest["close"] - prev["close"]) / prev["close"] if prev["close"] > 0 else 0
        vol_change = latest["volume"] / prev["volume"] if prev["volume"] > 0 else 1.0

        if price_change > 0.01 and vol_change > 1.3:
            score += 6
            details.append("放量上涨+6")
        elif price_change > 0.01 and vol_change < 0.8:
            score -= 3
            details.append("缩量上涨-3")
        elif price_change < -0.01 and vol_change > 1.3:
            score -= 6
            details.append("放量下跌-6")
        elif price_change < -0.01 and vol_change < 0.8:
            score += 3
            details.append("缩量下跌+3")

    # 因子3：ADX趋势强度（±6分）
    adx = latest.get("adx")
    if adx is not None:
        if adx >= 25:
            score += 6
            details.append("ADX强趋势+6")
        elif adx < 20:
            score -= 3
            details.append("ADX无趋势-3")
        else:
            adj = (adx - 20) * 1.8
            score += adj
            details.append(f"ADX中间+{adj:.1f}")

    # 因子4：价格位置（±3分）
    closes = [k["close"] for k in klines[:60] if k.get("close")]
    if len(closes) >= 20:
        max_c = max(closes)
        min_c = min(closes)
        if max_c > min_c:
            position = (latest["close"] - min_c) / (max_c - min_c)
            if position < 0.3:
                score += 3
                details.append("底部区域+3")
            elif position > 0.8:
                score -= 2
                details.append("高位区域-2")

    final_score = max(0.0, min(100.0, score))
    return DimensionScore(
        "volume_price", final_score, WEIGHTS["volume_price"],
        ", ".join(details) if details else f"基准{score:.0f}",
    )


# ════════════════════════════════════════════════════════════════
# 维度二：资金维度 Fund (25%)
#   主力净流入方向 ±8 | CMF ±6 | 大单占比 ±6 | 净流入相对规模 ±3
# ════════════════════════════════════════════════════════════════

def calculate_fund_score(fund_flow: list[dict]) -> DimensionScore:
    """资金维度评分 — 基准50，±23分范围"""
    score = 50.0
    details: list[str] = []

    if len(fund_flow) == 0:
        return DimensionScore("fund", score, WEIGHTS["fund"], "无资金流数据")

    latest_ff = fund_flow[0]

    # 因子1：主力资金净流入方向（±8分）
    consecutive_inflow = 0
    consecutive_outflow = 0
    for ff in fund_flow:
        ma = ff.get("main_amount")
        if ma is not None:
            if ma > 0:
                consecutive_inflow += 1
                if consecutive_outflow > 0:
                    break
            elif ma < 0:
                consecutive_outflow += 1
                if consecutive_inflow > 0:
                    break

    if consecutive_inflow >= 3:
        score += 8
        details.append(f"连续{consecutive_inflow}日主力净流入+8")
    elif consecutive_inflow == 2:
        score += 5
        details.append("连续2日主力净流入+5")
    elif consecutive_inflow == 1:
        score += 2
        details.append("单日主力净流入+2")

    if consecutive_outflow >= 3:
        score -= 8
        details.append(f"连续{consecutive_outflow}日主力净流出-8")
    elif consecutive_outflow == 2:
        score -= 5
        details.append("连续2日主力净流出-5")
    elif consecutive_outflow == 1:
        score -= 2
        details.append("单日主力净流出-2")

    # 因子2：CMF资金流向（±6分）
    cmf = latest_ff.get("cmf")
    if cmf is not None:
        if cmf > 0:
            score += 3
            details.append("CMF>0+3")
            if len(fund_flow) >= 3:
                all_positive = all(ff.get("cmf") is not None and ff["cmf"] > 0 for ff in fund_flow[:3])
                if all_positive:
                    score += 3
                    details.append("连续3日CMF>0+3")
        elif cmf < 0:
            score -= 3
            details.append("CMF<0-3")
            if len(fund_flow) >= 3:
                all_negative = all(ff.get("cmf") is not None and ff["cmf"] < 0 for ff in fund_flow[:3])
                if all_negative:
                    score -= 3
                    details.append("连续3日CMF<0-3")

    # 因子3：大单占比（±6分）
    lop = latest_ff.get("large_order_pct")
    if lop is not None:
        if lop > 0.30:
            score += 6
            details.append(f"大单占比{lop:.0%}+6")
        elif lop > 0.20:
            score += 3
            details.append(f"大单占比{lop:.0%}+3")
        elif lop < 0.10:
            score -= 3
            details.append(f"大单占比{lop:.0%}-3")

    # 因子4：净流入相对规模（±3分）
    ma = latest_ff.get("main_amount")
    na = latest_ff.get("net_amount")
    if ma is not None and na is not None and na != 0:
        ratio = abs(ma) / abs(na)
        if ratio > 0.5:
            score += 3
            details.append("主力净流入占主导+3")
        elif ratio < 0.2:
            score -= 2
            details.append("主力参与微弱-2")

    final_score = max(0.0, min(100.0, score))
    return DimensionScore(
        "fund", final_score, WEIGHTS["fund"],
        ", ".join(details) if details else "基准",
    )


# ════════════════════════════════════════════════════════════════
# 维度三：情绪维度 Sentiment (15%)
#   新闻情绪 ±6 | 板块热度 ±6 | 龙虎榜 ±3 | 时效性 ±3
# ════════════════════════════════════════════════════════════════

def calculate_sentiment_score(news: list[dict], trade_date: str) -> DimensionScore:
    """情绪维度评分 — 基准50，±18分范围

    P0简化版：无新闻源时基于板块热度做简化判断。
    后续由Agent在DD-04中提供真正的情绪分析。
    """
    score = 50.0
    details: list[str] = []

    if not news:
        return DimensionScore("sentiment", score, WEIGHTS["sentiment"], "无新闻数据")

    # 因子1：新闻情绪标签统计（±6分）
    positive_count = 0
    negative_count = 0
    for n in news:
        sent = n.get("sentiment")
        if sent == "positive":
            positive_count += 1
        elif sent == "negative":
            negative_count += 1
        elif n.get("category") == "finance" and n.get("is_hot"):
            positive_count += 1

    if positive_count + negative_count > 0:
        sentiment_ratio = (positive_count - negative_count) / (positive_count + negative_count)
        if sentiment_ratio > 0.3:
            score += 6
            details.append("正面情绪占优+6")
        elif sentiment_ratio > 0:
            score += 3
            details.append("正面+3")
        elif sentiment_ratio < -0.3:
            score -= 6
            details.append("负面情绪占优-6")
        elif sentiment_ratio < 0:
            score -= 3
            details.append("负面-3")

    # 因子2：板块热度（±6分） — P0用sector_data中的板块涨跌数量判断
    # 本函数从外部传入，呼入时已聚合好
    hot_sectors = news[0].get("_hot_sectors", 0) if news else 0
    cold_sectors = news[0].get("_cold_sectors", 0) if news else 0

    if hot_sectors >= 3:
        score += 6
        details.append(f"{hot_sectors}个活跃板块+6")
    elif hot_sectors >= 1:
        score += 3
        details.append(f"{hot_sectors}个活跃板块+3")

    if cold_sectors >= 10:
        score -= 6
        details.append(f"{cold_sectors}个下跌板块-6")

    # 因子3：龙虎榜（±3分） — P0简化
    dragon_tiger = any("龙虎榜" in str(n.get("title", "")) for n in news)
    if dragon_tiger:
        score += 3
        details.append("龙虎榜+3")

    # 因子4：时效性衰减
    # P0简化：传入的news中附带了时效性标记
    staleness = news[0].get("_staleness", 0) if news else 0
    if staleness >= 2 and len(news) > 0:
        score -= 3
        details.append("时效性差-3")

    final_score = max(0.0, min(100.0, score))
    return DimensionScore(
        "sentiment", final_score, WEIGHTS["sentiment"],
        ", ".join(details) if details else "基准",
    )


# ════════════════════════════════════════════════════════════════
# 维度四：主力行为维度 Mainforce (25%)
#   6因子：K线形态 +3 | 下杀后缩量 ±3 | 价格位置 ±3 |
#          消息面 ±3(暂不启用) | 大单行为 ±3 | 连流方向 ±3
# ════════════════════════════════════════════════════════════════

def calculate_mainforce_score(klines: list[dict], fund_flow: list[dict]) -> DimensionScore:
    """主力行为维度评分 — 基准50，总分范围0-100

    你的核心武器：识别洗盘vs出货。P0实现6因子简化版。
    """
    score = 50.0
    details: list[str] = []

    if len(klines) < 3:
        return DimensionScore("mainforce", score, WEIGHTS["mainforce"], "K线不足3根")

    latest = klines[0]

    # 因子1：K线形态 — 大阴线后收小阳线/十字星，倾向洗盘（+3分）
    big_drop_day = None
    for k in klines[:5]:
        if k.get("open", 0) > 0 and (k["close"] - k["open"]) / k["open"] <= -0.05:
            big_drop_day = k
            break

    if big_drop_day is not None:
        days_after = [k for k in klines if k.get("trade_date", "") > big_drop_day.get("trade_date", "")][:2]
        for d in days_after:
            if d.get("open", 0) > 0:
                body_pct = abs(d["close"] - d["open"]) / d["open"] * 100
                if d["close"] > d["open"] and body_pct < 2:
                    score += 3
                    details.append("大阴后小阳线(洗盘)+3")
                    break

    # 因子2：成交量 — 下杀日放量→次日急剧缩量（+3分），持续放量（-3分）
    if big_drop_day is not None and len(klines) >= 2:
        next_day = klines[0]
        if big_drop_day["volume"] > 0:
            vol_ratio = next_day["volume"] / big_drop_day["volume"]
            if vol_ratio < 0.60:
                score += 3
                details.append(f"下杀后缩量{vol_ratio:.0%}+3")
            elif vol_ratio > 1.0:
                score -= 3
                details.append(f"持续放量{vol_ratio:.0%}-3")

    # 因子3：价格位置 — 跌20%以上底部区（+3），涨50%以上高位区（-3）
    closes = [k["close"] for k in klines if k.get("close")]
    if len(closes) >= 20:
        max_c = max(closes)
        min_c = min(closes)
        if max_c > min_c:
            position = (latest["close"] - min_c) / (max_c - min_c)
            if position < 0.3:
                score += 3
                details.append("低位+3")
            elif position > 0.8:
                score -= 3
                details.append("高位-3")

    # 因子4：消息面（P0暂不启用，等待Agent）
    # 产品设计需要Agent分析新闻情绪标签

    # 因子5：大单行为 — 下跌中大单净流入（+3），净流出（-3）
    if len(fund_flow) > 0:
        ff = fund_flow[0]
        ma = ff.get("main_amount")
        if ma is not None:
            if ma > 0:
                score += 3
                details.append("主力净流入+3")
            elif ma < 0:
                score -= 3
                details.append("主力净流出-3")

    # 因子6：资金流向连贯性（±3分）
    # 连续3日主力净流入/净流出一致性加分
    if len(fund_flow) >= 3:
        positive_days = sum(1 for ff in fund_flow[:3] if ff.get("main_amount", 0) > 0)
        negative_days = sum(1 for ff in fund_flow[:3] if ff.get("main_amount", 0) < 0)
        if positive_days >= 2:
            score += 3
            details.append("资金连流一致性+3")
        elif negative_days >= 2:
            score -= 3
            details.append("资金连流一致性-3")

    final_score = max(0.0, min(100.0, score))
    return DimensionScore(
        "mainforce", final_score, WEIGHTS["mainforce"],
        ", ".join(details) if details else "基准",
    )


# ════════════════════════════════════════════════════════════════
# 维度五：资本市场逻辑维度 CapitalLogic (15%)
#   板块政策赛道 ±8 | 驱动事件 ±6 | 估值分位数 ±3
# ════════════════════════════════════════════════════════════════

def calculate_capital_logic_score(
    candidate: dict,
    news: list[dict],
    klines: list[dict],
) -> DimensionScore:
    """资本市场逻辑维度评分 — 基准50，±17分范围"""
    score = 50.0
    details: list[str] = []

    # 因子1：板块政策赛道判断（±8分）
    # P0简化：通过sector_data中的capital_ratio和sector换手率判断
    sectors = candidate.get("_sectors", [])
    for sec in sectors:
        cr = sec.get("capital_ratio")
        if cr is not None:
            if cr > 0.12:
                score += 4
                details.append(f"板块资金集中度>{cr:.0%}+4")
            elif cr > 0.06:
                score += 2
                details.append(f"板块资金集中度>{cr:.0%}+2")
            elif cr < -0.05:
                score -= 3
                details.append("板块资金流出-3")

    if len(sectors) >= 2:
        positive_sectors = sum(1 for s in sectors if s.get("change_pct", 0) > 0)
        if positive_sectors >= 2:
            score += 4
            details.append("多板块共振+4")

    # 因子2：近期驱动事件（±6分）
    if news:
        policy_kw = ["政策", "利好", "补贴", "扶持", "规划", "战略", "新基建"]
        event_kw = ["业绩预增", "中标", "合同", "重组", "并购", "回购"]
        negative_kw = ["处罚", "违规", "退市", "诉讼", "减持", "质押"]

        policy_hits = 0
        event_hits = 0
        negative_hits = 0

        for n in news:
            title = str(n.get("title", ""))
            for kw in policy_kw:
                if kw in title:
                    policy_hits += 1
                    break
            for kw in event_kw:
                if kw in title:
                    event_hits += 1
                    break
            for kw in negative_kw:
                if kw in title:
                    negative_hits += 1
                    break

        if policy_hits >= 2:
            score += 6
            details.append(f"{policy_hits}条政策利好+6")
        elif policy_hits == 1:
            score += 3
            details.append("政策利好+3")

        if event_hits >= 2:
            score += 4
            details.append(f"{event_hits}条事件驱动+4")
        elif event_hits == 1:
            score += 2
            details.append("事件驱动+2")

        if negative_hits >= 1:
            score -= 6
            details.append("负面事件-6")

    # 因子3：估值分位数（±3分）
    closes = [k["close"] for k in klines[:120] if k.get("close")]
    if len(closes) >= 60:
        max_c = max(closes)
        min_c = min(closes)
        current = klines[0]["close"] if klines else 0
        if max_c > min_c and current > 0:
            percentile = (current - min_c) / (max_c - min_c)
            if percentile < 0.25:
                score += 3
                details.append("估值低位+3")
            elif percentile > 0.75:
                score -= 3
                details.append("估值高位-3")

    final_score = max(0.0, min(100.0, score))
    return DimensionScore(
        "capital_logic", final_score, WEIGHTS["capital_logic"],
        ", ".join(details) if details else "基准",
    )


# ════════════════════════════════════════════════════════════════
# 主评分入口
# ════════════════════════════════════════════════════════════════

def score_candidates(
    candidates: list,
    klines_map: dict[str, list[dict]] | None = None,
    fund_flow_map: dict[str, list[dict]] | None = None,
    news_map: dict[str, list[dict]] | None = None,
    trade_date: str | None = None,
) -> list[ScoredCandidate]:
    """对候选列表进行五维度评分，返回取前15名

    Args:
        candidates: StrategyCandidate 列表（带detail字段）
        klines_map: {code: [kline_dict, ...]} K线数据，DESC排序
        fund_flow_map: {code: [fund_dict, ...]} 资金流数据，DESC排序
        news_map: {code: [news_dict, ...]} 新闻数据
        trade_date: 交易日期字符串 YYYY-MM-DD
    """
    if not candidates:
        return []

    results: list[ScoredCandidate] = []

    for c in candidates:
        code = c.stock_code
        klines = (klines_map or {}).get(code, [])
        fund_flow = (fund_flow_map or {}).get(code, [])
        news = (news_map or {}).get(code, [])

        # 五维度评分
        dim_vp = calculate_volume_price_score(klines)
        dim_fund = calculate_fund_score(fund_flow)
        dim_sent = calculate_sentiment_score(news, trade_date or "")
        dim_mf = calculate_mainforce_score(klines, fund_flow)
        dim_logic = calculate_capital_logic_score(c.detail, news, klines)

        dims = {
            "volume_price": dim_vp,
            "fund": dim_fund,
            "sentiment": dim_sent,
            "mainforce": dim_mf,
            "capital_logic": dim_logic,
        }

        total = sum(d.weighted for d in dims.values())
        strategy_type = c.detail.get("strategy", "")

        results.append(ScoredCandidate(
            stock_code=code,
            stock_name=c.stock_name,
            strategy_type=strategy_type,
            score_total=round(total, 2),
            score_volume=round(dim_vp.score, 2),
            score_fund=round(dim_fund.score, 2),
            score_sentiment=round(dim_sent.score, 2),
            score_mainforce=round(dim_mf.score, 2),
            score_logic=round(dim_logic.score, 2),
            dimensions=dims,
            reason=c.reason,
        ))

    # 按总分降序
    results.sort(key=lambda r: r.score_total, reverse=True)
    top_15 = results[:15]

    # 评分截断检测
    if len(top_15) >= 6:
        gap = top_15[4].score_total - top_15[5].score_total
        if gap >= 15:
            logger.info(
                "评分截断检测: 前5名与第6名分差%.1f分 (n=%d candidate)",
                gap, len(results),
            )

    return top_15
