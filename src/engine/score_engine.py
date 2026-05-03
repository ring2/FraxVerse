"""多维评分引擎 — 给候选股票打多维度分数

数据源：东方财富 push2 免费API（已验证可用）
维度：
  1. 量价维度 (30%) — 成交量变化率、价量配合
  2. 资金维度 (25%) — 主力净流入、大单占比
  3. 板块维度 (20%) — 所属板块热度、板块资金流
  4. 盘口维度 (15%) — 内外盘比、委比
  5. 情绪维度 (10%) — 涨跌趋势反转信号

使用方式：
  from src.engine.score_engine import ScoreEngine
  engine = ScoreEngine()
  result = engine.score(code="600519")

缓存策略：
  - 板块资金流排名：60秒
  - 实时行情/盘口：5秒（指数直接调用）
  - 个股资金流：1小时（日级数据不变）
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ─── 东方财富 push2 API 基础 ───
_PUSH2 = "https://push2.eastmoney.com/api/qt"
_CLIST = f"{_PUSH2}/clist/get"
_STOCK = f"{_PUSH2}/stock/get"
_FFLOW = f"{_PUSH2}/stock/fflow/daykline/get"

# 维度权重（总和100）
WEIGHTS = {
    "volume_price": 0.30,  # 量价
    "fund_flow": 0.25,     # 资金
    "sector": 0.20,        # 板块
    "order_book": 0.15,    # 盘口
    "sentiment": 0.10,     # 情绪
}

# ─── 交易所映射 ───
def _market(code: str) -> int:
    c = code.strip().upper()
    if c.startswith(("6", "9")):
        return 1
    if c.startswith(("0", "3")):
        return 0
    if c.startswith(("4", "8")):
        return 2
    return 1


def _fetch_json(url: str, params: dict, timeout: int = 5) -> dict | None:
    """通用 GET 请求 + JSON 解析"""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        data = resp.json()
        if data.get("rc") == 0 and data.get("data"):
            return data["data"]
    except Exception as e:
        logger.warning("请求失败 %s %s: %s", url, params, e)
    return None


# ─── 维度评分函数 ───

def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _score_volume_price(row: dict) -> float:
    """量价维度 (0-100)：基于实时行情的成交量变化率和价格位置

    需要的字段(从 push2 stock/get 获取):
        f47: 成交量(手), f48: 成交额(元)
        f43: 最新价(÷100), f44: 最高(÷100), f45: 最低(÷100)
        f170: 涨跌幅(÷100), f169: 涨跌额(÷100)
        f50: 振幅(÷100)
    """
    change_pct = _safe_float(row.get("f170", 0)) / 100  # 涨跌幅%
    amplitude = _safe_float(row.get("f50", 0)) / 100     # 振幅%
    vol = _safe_float(row.get("f47", 0))                 # 成交量(手)
    price = _safe_float(row.get("f43", 0)) / 100
    high = _safe_float(row.get("f44", 0)) / 100
    low = _safe_float(row.get("f45", 0)) / 100

    score = 50.0

    # 1) 涨跌幅分：-3%~+3% 是中性区，超跌加分，暴涨不追
    if change_pct < -2:
        score += min(abs(change_pct) * 6, 20)   # 超跌加分
    elif -2 <= change_pct < -0.5:
        score += 8   # 小幅调整，加仓机会
    elif change_pct > 3:
        score -= min((change_pct - 3) * 5, 15)  # 暴涨减分

    # 2) 量价配合：放量下跌要警惕，缩量下跌反而好
    # 振幅大+跌幅小 = 有承接
    if amplitude > 2 and change_pct > -1:
        score += 10  # 振幅大但没跌，有资金承接
    elif amplitude > 3 and change_pct < -2:
        score -= 10  # 放量大跌

    # 3) 价格位置：中低位加分
    if high > low:
        pos_ratio = (price - low) / (high - low) if (high - low) > 0 else 0.5
        if pos_ratio < 0.3:
            score += 10   # 靠近日内低点，低吸机会
        elif pos_ratio > 0.8:
            score -= 8    # 靠近日内高点，追高风险

    return max(0, min(100, score))


def _score_fund_flow(code: str, market: int) -> float:
    """资金维度 (0-100)：基于个股资金流向

    需要的接口: push2 stock/fflow/daykline/get
    字段: 主力净流入、超大单净占比、大单净占比、小单净占比
    """
    params = {
        "secid": f"{market}.{code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "lmt": 1,
        "klt": 101,
    }
    data = _fetch_json(_FFLOW, params)
    if not data or not data.get("klines"):
        return 50.0

    parts = data["klines"][0].split(",")
    # parts[0]=日期, [1]=主力净流入, [6]=超大单净占比, [8]=大单净占比
    # [9]=中单净占比, [10]=小单净占比
    main_net = _safe_float(parts[1])      # 主力净流入(元)
    big_order_pct = _safe_float(parts[8])  # 大单净占比(%)
    small_order_pct = _safe_float(parts[10])  # 小单净占比(%)

    score = 50.0

    # 主力净流入：流入加分，流出减分
    if main_net > 0:
        score += min(main_net / 10_000_000, 20)  # 每千万流入+1分，上限20
    else:
        score -= min(abs(main_net) / 10_000_000, 15)

    # 大单占比：正占比=主力买入多
    if big_order_pct > 5:
        score += 10
    elif big_order_pct > 0:
        score += 5

    # 小单占比高 = 散户主导，不好
    if small_order_pct > 10:
        score -= 8

    return max(0, min(100, score))


def _score_sector(code: str, market: int) -> float:
    """板块维度 (0-100)：个股所属板块的热度

    步骤：
      1. 从 stock/get 获取板块信息
      2. 从 clist 获取该板块的涨跌幅 + 资金流
    需要字段: f127=行业, f129=概念(逗号分隔)
    """
    # 1) 获取所属板块
    params = {"secid": f"{market}.{code}", "fields": "f127,f128,f129"}
    data = _fetch_json(_STOCK, params)
    if not data:
        return 50.0

    # 行业
    industry = str(data.get("f127", "")).strip()
    if not industry:
        return 50.0

    score = 50.0

    # 2) 查该行业板块在 clist 中的排名
    clist_params = {
        "pn": 1, "pz": 200, "po": 1, "np": 1,
        "fs": "m:90+t:1",  # 行业板块
        "fields": "f2,f3,f4,f12,f14,f62,f184",
        "fid": "f3",
    }
    sector_data = _fetch_json(_CLIST, clist_params)
    if sector_data and sector_data.get("diff"):
        items = sector_data["diff"]
        # 行业名模糊匹配：去掉末尾的罗马数字/ⅡⅢ等
        import re as _re
        clean_industry = _re.sub(r"[ⅠⅡⅢⅣⅤⅥ]|\\d+$", "", industry).strip()
        for i, item in enumerate(items):
            name = str(item.get("f14", "")).strip()
            clean_name = _re.sub(r"[ⅠⅡⅢⅣⅤⅥ]|\\d+$", "", name).strip()
            if clean_industry == clean_name or clean_industry.startswith(clean_name) or clean_name.startswith(clean_industry):
                rank = i + 1
                total = len(items)
                rank_ratio = rank / total
                rank_score = 70 * (1 - rank_ratio) + 30
                score = max(score, rank_score)

                # 主力净流入加成
                net_flow = _safe_float(item.get("f62", 0))
                if net_flow > 1_000_000:     # >1亿净流入
                    score += 10
                elif net_flow < -1_000_000:
                    score -= 8
                break

        # 概念板块也加分（如果有热门概念）
        concepts = str(data.get("f129", "")).strip()
        hot_concepts = {"人工智能", "芯片", "半导体", "新能源", "机器人",
                        "华为", "AI", "算力", "低空经济", "固态电池"}
        if any(c in concepts for c in hot_concepts):
            score += 8

    return max(0, min(100, score))


def _score_order_book(row: dict) -> float:
    """盘口维度 (0-100)：改用振幅+量比反映买卖强度

    需要的字段:
        f50: 振幅(÷100), f49: 量比(÷10000)
    """
    amplitude = _safe_float(row.get("f50", 0)) / 100      # 振幅%
    vol_ratio = _safe_float(row.get("f49", 0)) / 10000    # 量比

    score = 50.0

    # 量比：>1.2放量，<0.8缩量，适中最好
    if 0.8 <= vol_ratio <= 1.5:
        score += 15  # 量能适中，健康
    elif 1.5 < vol_ratio <= 2.5:
        score += 10  # 温和放量，有资金进场
    elif vol_ratio > 3:
        score -= 10  # 巨量，警惕出货
    elif vol_ratio < 0.5:
        score -= 8   # 极度缩量，无人问津

    # 振幅：适当振幅反映活跃度
    if 1.5 <= amplitude <= 3.5:
        score += 10  # 活跃但不过度
    elif amplitude < 0.5:
        score -= 5   # 死水一潭
    elif amplitude > 5:
        score -= 8   # 剧烈波动

    return max(0, min(100, score))


def _score_sentiment(row: dict) -> float:
    """情绪维度 (0-100)：技术反转信号和涨跌速

    需要的字段(从 push2 stock/get 获取):
        f170: 涨跌幅(÷100), f171: 涨速(÷100)
        f169: 涨跌额(÷100), f50: 振幅(÷100)
    """
    change_pct = _safe_float(row.get("f170", 0)) / 100
    speed = _safe_float(row.get("f171", 0)) / 100   # 涨速

    score = 50.0

    # 1) 涨速为正 + 涨幅不大 = 启动信号
    if speed > 0.3 and -1 < change_pct < 2:
        score += 15

    # 2) 跌幅放缓（小跌+正涨速）= 止跌信号
    if -1.5 < change_pct < -0.1 and speed > 0.1:
        score += 12

    # 3) 急速拉升（涨速>0.5）+ 涨幅已大 = 追高风险
    if speed > 0.5 and change_pct > 3:
        score -= 15

    # 4) 横盘整理（小涨跌）= 蓄力等待方向
    if abs(change_pct) < 0.3 and abs(speed) < 0.1:
        score += 5

    return max(0, min(100, score))


# ─── 主引擎 ───

class ScoreEngine:
    """多维度评分引擎"""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or WEIGHTS

    def score(self, code: str) -> dict[str, Any]:
        """对单只股票进行多维度评分

        Args:
            code: 股票代码，如 "600519"

        Returns:
            {
                "score_total": float,      # 总分 (0-100)
                "score_volume": float,     # 量价分
                "score_fund": float,       # 资金分
                "score_sector": float,     # 板块分
                "score_order_book": float, # 盘口分
                "score_sentiment": float,  # 情绪分
                "details": {
                    "name": str,
                    "price": float,
                    "change_pct": float,
                    "volume_ratio": float,
                    "pe": float,
                    "pb": float,
                    "turnover_rate": float,
                }
            }
        """
        raw_code = code.strip().upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        market = _market(raw_code)
        secid = f"{market}.{raw_code}"

        # 1) 获取实时行情（所有维度共用）
        stock_params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f57,f58,f116,f117,f162,f167,f168,f169,f170,f171,f292",
        }
        stock_data = _fetch_json(_STOCK, stock_params)
        if not stock_data:
            logger.warning("无法获取 %s 实时行情", code)
            return self._empty_result(code)

        row = stock_data

        # 2) 逐维度评分
        sv = _score_volume_price(row)
        sf = _score_fund_flow(raw_code, market)
        ss = _score_sector(raw_code, market)
        so = _score_order_book(row)
        se = _score_sentiment(row)

        # 3) 加权总分
        total = (
            sv * self.weights["volume_price"]
            + sf * self.weights["fund_flow"]
            + ss * self.weights["sector"]
            + so * self.weights["order_book"]
            + se * self.weights["sentiment"]
        )

        name = str(row.get("f58", ""))
        price = _safe_float(row.get("f43", 0)) / 100
        change_pct = _safe_float(row.get("f170", 0)) / 100
        volume_ratio = _safe_float(row.get("f49", 0)) / 10000
        pe = _safe_float(row.get("f162", 0)) / 100
        pb = _safe_float(row.get("f167", 0)) / 100
        turnover = _safe_float(row.get("f168", 0)) / 100

        return {
            "code": raw_code,
            "score_total": round(max(0, min(100, total)), 1),
            "score_volume": round(max(0, min(100, sv)), 1),
            "score_fund": round(max(0, min(100, sf)), 1),
            "score_sector": round(max(0, min(100, ss)), 1),
            "score_order_book": round(max(0, min(100, so)), 1),
            "score_sentiment": round(max(0, min(100, se)), 1),
            "details": {
                "name": name,
                "price": price,
                "change_pct": change_pct,
                "volume_ratio": volume_ratio,
                "pe": pe,
                "pb": pb,
                "turnover_rate": turnover,
            },
        }

    def _empty_result(self, code: str) -> dict:
        return {
            "code": code,
            "score_total": 0,
            "score_volume": 0,
            "score_fund": 0,
            "score_sector": 0,
            "score_order_book": 0,
            "score_sentiment": 0,
            "details": {
                "name": code, "price": 0, "change_pct": 0,
                "volume_ratio": 0, "pe": 0, "pb": 0, "turnover_rate": 0,
            },
        }


# ─── 批量扫描 ───

def batch_score(codes: list[str],
                weights: dict[str, float] | None = None,
                strategy: str = "trend_momentum") -> list[dict]:
    """批量扫描评分，按总分降序排序

    Args:
        codes: 股票代码列表
        weights: 权重覆盖
        strategy: 策略类型，存入结果

    Returns:
        按总分降序的评分结果列表
    """
    engine = ScoreEngine(weights=weights)
    results = []

    for code in codes:
        r = engine.score(code)
        if r["score_total"] > 0:
            r["strategy_type"] = strategy
            results.append(r)
            logger.info("%s 评分: %.1f (量价%.1f 资金%.1f 板块%.1f 盘口%.1f 情绪%.1f)",
                        code, r["score_total"],
                        r["score_volume"], r["score_fund"],
                        r["score_sector"], r["score_order_book"], r["score_sentiment"])

    results.sort(key=lambda x: x["score_total"], reverse=True)
    return results
