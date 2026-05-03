"""策略扫描路由 — /api/v1/strategy/scan

用于前端"重新扫描"按钮：多维度评分→筛选候选→入库 stock_pool。

评分引擎: src.engine.score_engine.ScoreEngine
数据源: 东方财富 push2 免费API（板块资金流、个股资金流、实时行情）
"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.session import get_session
from src.engine.score_engine import batch_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])

# 30只A股样本（沪深300核心权重股 + 各行业龙头）
_STOCK_SAMPLE = [
    # 消费/白酒
    "600519", "000858", "600887", "002304", "000568",
    # 新能源/汽车
    "300750", "002594", "601012", "300274", "002129",
    # 金融
    "600036", "601166", "601318", "600030", "000002",
    # 科技/制造
    "002415", "000333", "600276", "688981", "002371",
    # 能源/资源
    "601857", "600028", "601899", "600900", "000630",
    # 通信/基建
    "601728", "600941", "601668", "600585", "000001",
]

# 策略权重配置
_STRATEGY_CONFIG = {
    "bottom_reversal": {
        "weights": {
            "volume_price": 0.35,  # 量价权重加大（找超跌反弹）
            "fund_flow": 0.20,
            "sector": 0.15,
            "order_book": 0.15,
            "sentiment": 0.15,
        },
        "min_score": 50,
    },
    "trend_momentum": {
        "weights": {
            "volume_price": 0.25,
            "fund_flow": 0.25,     # 资金权重加大（找主力介入）
            "sector": 0.20,
            "order_book": 0.15,
            "sentiment": 0.15,
        },
        "min_score": 50,
    },
    "bottom_volume": {
        "weights": {
            "volume_price": 0.30,
            "fund_flow": 0.25,
            "sector": 0.20,
            "order_book": 0.15,
            "sentiment": 0.10,
        },
        "min_score": 50,
    },
}


@router.post("/scan")
def scan_stock_pool(
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """多维度评分扫描：全样本评分→分策略筛选→入库

    返回扫描摘要。
    """
    today = date.today().isoformat()
    all_candidates = []

    # ── 1. 对每个策略做一次评分筛选 ──
    for strategy_name, config in _STRATEGY_CONFIG.items():
        results = batch_score(
            codes=_STOCK_SAMPLE,
            weights=config["weights"],
            strategy=strategy_name,
        )
        for r in results:
            if r["score_total"] >= config["min_score"]:
                full_code = _to_full_code(r["details"].get("code", _extract_code(r)))
                all_candidates.append({
                    "stock_code": full_code,
                    "stock_name": r["details"].get("name", ""),
                    "strategy_type": strategy_name,
                    "score_total": r["score_total"],
                    "score_volume": r["score_volume"],
                    "score_fund": r["score_fund"],
                    "score_sector": r["score_sector"],
                    "score_order_book": r["score_order_book"],
                    "score_sentiment": r["score_sentiment"],
                })

    # 去重：同一只股票优先保留评分最高的策略
    seen: dict[str, dict] = {}
    for c in all_candidates:
        code = c["stock_code"]
        if code not in seen or c["score_total"] > seen[code]["score_total"]:
            seen[code] = c
    all_candidates = list(seen.values())

    # 按评分降序
    all_candidates.sort(key=lambda x: x["score_total"], reverse=True)

    # ── 2. 写入 stocks 表（中文名） ──
    for c in all_candidates:
        code = c["stock_code"]
        short_code = code.replace(".SH", "").replace(".SZ", "")
        name = c.get("stock_name", short_code)
        try:
            db.execute(
                text("""INSERT INTO stocks (code, name, market)
                        VALUES (:c, :n, :m)
                        ON CONFLICT (code) DO UPDATE SET name = :n"""),
                {"c": code, "n": name, "m": "SH" if ".SH" in code else "SZ"},
            )
        except Exception as e:
            logger.warning("更新stocks失败 %s: %s", code, e)

    db.commit()

    # ── 3. 写入 stock_pool 表 ──
    try:
        db.execute(text("DELETE FROM stock_pool WHERE date = :d"), {"d": today})
        db.commit()
    except Exception as e:
        logger.warning("删除旧数据失败: %s", e)
        db.rollback()

    inserted = 0
    for c in all_candidates:
        try:
            db.execute(
                text("""
                    INSERT INTO stock_pool
                        (date, stock_code, strategy_type, pass_coarse,
                         score_total, position_pct, score_volume, score_fund,
                         score_sentiment, score_mainforce)
                    VALUES
                        (:date, :stock_code, :strategy_type, TRUE,
                         :score_total, 0, :score_volume, :score_fund,
                         :score_sentiment, :score_order_book)
                """),
                {
                    "date": today,
                    "stock_code": c["stock_code"],
                    "strategy_type": c["strategy_type"],
                    "score_total": c["score_total"],
                    "score_volume": c["score_volume"],
                    "score_fund": c["score_fund"],
                    "score_sentiment": c["score_sentiment"],
                    "score_order_book": c["score_order_book"],
                },
            )
            inserted += 1
        except Exception as e:
            logger.warning("入库失败 %s: %s", c["stock_code"], e)

    db.commit()

    logger.info("多维度扫描完成，入库 %d/%d 条", inserted, len(all_candidates))

    return {
        "code": 0,
        "message": f"多维度评分扫描完成，入库 {inserted} 只标的",
        "data": {
            "total": len(all_candidates),
            "inserted": inserted,
            "stockCount": len(_STOCK_SAMPLE),
            "timestamp": datetime.now().isoformat(),
        },
    }


def _to_full_code(raw: str) -> str:
    """补全交易所后缀"""
    r = raw.strip().upper()
    if "." in r:
        return r
    if r.startswith(("6", "9")):
        return f"{r}.SH"
    return f"{r}.SZ"


def _extract_code(r: dict) -> str:
    """从评分结果中提取代码——兜底"""
    return r.get("code", "")
