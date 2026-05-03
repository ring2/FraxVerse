"""策略扫描路由 — /api/v1/strategy/scan

用于前端"重新扫描"按钮：拉取样本股票K线、五维度评分、入库 stock_pool。
"""

import logging
from datetime import date, datetime

import akshare as ak
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])

# 20只A股样本（同 run_p0.py）
_STOCK_SAMPLE = [
    "600519", "000858", "600036", "601166", "600900",
    "601318", "000333", "600276", "002415", "300750",
    "600887", "002594", "601857", "600028", "688981",
    "601728", "601899", "000002", "601012", "600941",
]


@router.post("/scan")
def scan_stock_pool(
    db: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """执行股票池扫描：拉取20只样本股票最新K线 → 简略评分 → 入库。

    返回扫描摘要（扫描到的股票数、入库数）。
    """
    today = date.today().isoformat()

    # ── 1. 从 AKShare 获取真实K线 ──
    klines_dict: dict[str, pd.DataFrame] = {}
    stock_names: dict[str, str] = {}
    success = 0

    for code in _STOCK_SAMPLE:
        try:
            prefix = "sh" if code.startswith("6") or code.startswith("9") else "sz"
            df = ak.stock_zh_a_daily(symbol=f"{prefix}{code}", adjust="qfq")
            if df.empty:
                continue
            df = df.rename(columns={
                "open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volume": "Volume", "amount": "amount",
            })
            df["date"] = pd.to_datetime(df["date"])
            # 过滤最近60个交易日
            df = df.tail(60)
            if df.empty:
                continue
            df["pct_change"] = df["Close"].pct_change() * 100
            df = df.sort_values("date").reset_index(drop=True)

            full_code = f"{code}.SH" if code.startswith("6") or code.startswith("9") else f"{code}.SZ"
            klines_dict[full_code] = df
            stock_names[full_code] = code
            success += 1
        except Exception as e:
            logger.warning("获取 %s 失败: %s", code, e)

    logger.info("扫描获取 %d/20 只股票K线", success)

    # ── 2. 简略评分（基于最近5日涨跌幅分布） ──
    candidates_s1 = []  # 策略一：周期底部
    candidates_s2 = []  # 策略二：趋势动量

    for code, df in klines_dict.items():
        if df.empty:
            continue
        latest = df.iloc[-1]
        pct = float(latest.get("pct_change", 0)) if pd.notna(latest.get("pct_change")) else 0.0

        # 最近5日平均涨跌幅
        recent = df.tail(5)
        avg_pct = float(recent["pct_change"].mean()) if len(recent) > 0 else 0.0

        # 策略一：底部量能异动（大跌后企稳）
        if avg_pct < -1.0:
            score = 50 + abs(avg_pct) * 8
            candidates_s1.append({
                "stock_code": code,
                "stock_name": stock_names.get(code, code),
                "score_total": min(round(score, 1), 95.0),
                "strategy_type": "bottom_volume",
                "pct": pct,
                "avg_pct": round(avg_pct, 2),
            })

        # 策略二：趋势动量低吸（小涨/横盘）
        if -0.8 < avg_pct < 1.2:
            score = 50 + (1.2 - abs(avg_pct)) * 15
            candidates_s2.append({
                "stock_code": code,
                "stock_name": stock_names.get(code, code),
                "score_total": min(round(score, 1), 90.0),
                "strategy_type": "trend_momentum",
                "pct": pct,
                "avg_pct": round(avg_pct, 2),
            })

    # 按评分降序，各取前15
    candidates_s1.sort(key=lambda x: x["score_total"], reverse=True)
    candidates_s2.sort(key=lambda x: x["score_total"], reverse=True)
    candidates_s1 = candidates_s1[:15]
    candidates_s2 = candidates_s2[:15]
    all_candidates = candidates_s1 + candidates_s2

    # ── 3. 写入 stock_pool 表 ──
    # 先确保所有候选股票在 stocks 表中有记录
    for c in all_candidates:
        code = c["stock_code"]
        existing = db.execute(text("SELECT 1 FROM stocks WHERE code = :c"), {"c": code}).fetchone()
        if not existing:
            try:
                # 从 stock_code 解析短码
                short_code = code.replace(".SH", "").replace(".SZ", "")
                db.execute(
                    text("INSERT INTO stocks (code, name, market) VALUES (:c, :n, :m) ON CONFLICT (code) DO NOTHING"),
                    {"c": code, "n": short_code, "m": "SH" if ".SH" in code else "SZ"},
                )
            except Exception as e:
                logger.warning("插入stocks失败 %s: %s", code, e)

    db.commit()

    # 删除该日存在的数据（重新扫描覆盖）
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
                         :score_total, 0, :score_total, :score_total,
                         :score_total, :score_total)
                """),
                {
                    "date": today,
                    "stock_code": c["stock_code"],
                    "strategy_type": c["strategy_type"],
                    "score_total": c["score_total"],
                },
            )
            inserted += 1
        except Exception as e:
            logger.warning("入库失败 %s: %s", c["stock_code"], e)

    db.commit()
    logger.info("扫描完成，入库 %d/%d 条", inserted, len(all_candidates))

    return {
        "code": 0,
        "message": f"扫描完成，获取 {success} 只股票K线，入库 {inserted} 只标的",
        "data": {
            "total": len(all_candidates),
            "inserted": inserted,
            "stockCount": success,
            "candidates_s1": len(candidates_s1),
            "candidates_s2": len(candidates_s2),
            "timestamp": datetime.now().isoformat(),
        },
    }
