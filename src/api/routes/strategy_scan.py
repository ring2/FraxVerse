"""策略扫描路由 — /api/v1/strategy/scan

用于前端"重新扫描"按钮：中证500成分股 → 多维度评分 → 筛选候选 → 入库 stock_pool。

评分引擎: src.engine.score_engine.ScoreEngine
数据源: 东方财富 push2 免费API（板块资金流、个股资金流、实时行情）
成分股: AKShare 中证指数 000905（中证500）
"""

import logging
from datetime import date, datetime

import akshare as ak
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.session import get_session
from src.engine.score_engine import batch_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])

# ── 中证500成分股缓存（避免每次扫描都拉AKShare） ──
_CSI500_CACHE: list[str] | None = None
_CSI500_CACHE_DATE: str | None = None


def _get_csi500_stocks() -> list[str]:
    """获取中证500成分股（6位代码，不含后缀）"""
    global _CSI500_CACHE, _CSI500_CACHE_DATE
    today = date.today().isoformat()
    if _CSI500_CACHE is not None and _CSI500_CACHE_DATE == today:
        return _CSI500_CACHE

    try:
        df = ak.index_stock_cons_csindex("000905")
        codes = df["成分券代码"].str.strip().str.zfill(6).tolist()
        _CSI500_CACHE = codes
        _CSI500_CACHE_DATE = today
        logger.info("获取中证500成分股共 %d 只", len(codes))
        return codes
    except Exception as e:
        logger.warning("获取中证500成分股失败: %s，使用缓存或回退", e)
        if _CSI500_CACHE is not None:
            return _CSI500_CACHE
        # 兜底：如果没有缓存也没有网络，就报空（后续逻辑会处理）
        return []


def _build_full_code(short: str) -> str:
    """6位代码补全交易所后缀"""
    short = short.strip().upper()
    if short.startswith(("6", "9")):
        return f"{short}.SH"
    return f"{short}.SZ"


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
        "min_score": 60,
    },
    "trend_momentum": {
        "weights": {
            "volume_price": 0.25,
            "fund_flow": 0.25,     # 资金权重加大（找主力介入）
            "sector": 0.20,
            "order_book": 0.15,
            "sentiment": 0.15,
        },
        "min_score": 60,
    },
    "bottom_volume": {
        "weights": {
            "volume_price": 0.30,
            "fund_flow": 0.25,
            "sector": 0.20,
            "order_book": 0.15,
            "sentiment": 0.10,
        },
        "min_score": 60,
    },
}


@router.post("/scan")
def scan_stock_pool(
    pool_date: str | None = Query(None, alias="pool_date"),
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """多维度评分扫描：中证500成分股 → 多策略评分 → 候选入库

    可指定 pool_date 参数按历史日期回扫（用于验证/测试），
    不传则默认扫今天。

    返回扫描摘要。
    """
    scan_date = pool_date if pool_date else date.today().isoformat()
    all_candidates = []

    # ── 0. 获取中证500成分股，过滤出 daily_klines 中有数据的 ──
    csi500_short = _get_csi500_stocks()
    if not csi500_short:
        logger.warning("中证500成分股获取为空，返回空结果")
        return {
            "code": 1,
            "message": "获取中证500成分股失败，请稍后重试",
            "data": {"total": 0, "inserted": 0, "stockCount": 0, "timestamp": datetime.now().isoformat()},
        }

    # 构造 full_code 列表
    csi500_full = [_build_full_code(c) for c in csi500_short]

    # 从 daily_klines 过滤出 scan_date 有数据的
    stock_rows = db.execute(
        text("""
            SELECT DISTINCT d.stock_code
            FROM daily_klines d
            WHERE d.trade_date = :d
              AND d.stock_code = ANY(:codes)
        """),
        {"d": scan_date, "codes": csi500_full},
    ).fetchall()

    if stock_rows:
        stock_codes = [r[0] for r in stock_rows]
        logger.info("中证500中日期 %s 有日K数据的: %d 只", scan_date, len(stock_codes))
    else:
        # fallback: 直接用全部500只（评分引擎遇到无数据的会跳过）
        stock_codes = csi500_full[:]
        logger.warning("日期 %s 在 daily_klines 无中证500数据，直接使用全部500只", scan_date)

    logger.info("扫描样本池: %d 只", len(stock_codes))

    # ── 1. 单轮评分筛选（不再分策略各跑一次，改为统一评分） ──
    # 使用统一权重（融合动量+底部+反转）
    unified_weights = {
        "volume_price": 0.30,
        "fund_flow": 0.25,
        "sector": 0.20,
        "order_book": 0.15,
        "sentiment": 0.10,
    }
    results = batch_score(
        codes=stock_codes,
        weights=unified_weights,
        strategy="scan",
    )
    for r in results:
        if r["score_total"] >= 60:  # 统一 min_score
            full_code = _to_full_code(r["details"].get("code", _extract_code(r)))
            all_candidates.append({
                "stock_code": full_code,
                "stock_name": r["details"].get("name", ""),
                "strategy_type": "scan",
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
        db.execute(text("DELETE FROM stock_pool WHERE date = :d"), {"d": scan_date})
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
                    "date": scan_date,
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

    logger.info("中证500多维度扫描完成，入库 %d/%d 条", inserted, len(all_candidates))

    return {
        "code": 0,
        "message": f"中证500评分扫描完成，入库 {inserted} 只标的",
        "data": {
            "total": len(all_candidates),
            "inserted": inserted,
            "stockCount": len(stock_codes),
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
