"""
FraxVerse · 统一调度入口

管理所有定时任务：
1. 新闻采集（collect_hot_news）— 每30分钟
2. 止损监视器（StopLossMonitor）— 每30秒
3. 数据质量检查（data_quality）— 每日收盘后
4. 经验归档（stop_loss → 自动写入经验库）
5. 开盘前复核（开盘前30分钟）

用法：
    python -m src.cron_scheduler --mode all       # 启动全部
    python -m src.cron_scheduler --mode news       # 仅新闻采集
    python -m src.cron_scheduler --mode stop-loss  # 仅止损监视器
    python -m src.cron_scheduler --once news       # 单次执行新闻采集
"""

import argparse
import hashlib
import json
import logging
import signal
import sys
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.data.news_collector import collect_hot_news
from src.data.data_quality import detect_suspension
from src.db.session import get_session
from src.monitor.stop_loss import StopLossMonitor

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# 调度间隔配置（秒）
# ═══════════════════════════════════════════════════════════════════

NEWS_INTERVAL = 1800           # 新闻采集：30分钟
STOP_LOSS_INTERVAL = 30        # 止损监视：30秒
DATA_QUALITY_INTERVAL = 86400  # 数据质量：24小时
PRE_MARKET_INTERVAL = 86400    # 开盘前复核：每天一次


# ═══════════════════════════════════════════════════════════════════
# 经验归档
# ═══════════════════════════════════════════════════════════════════

def archive_stop_loss_experience(
    stock_code: str,
    pnl_pct: float,
    trigger_price: float,
    cost_price: float,
    reason: str,
    holding_days: int = 0,
):
    """止损触发时自动归档为一条经验"""
    try:
        from src.db.models import Experiences
        from src.db.session import SessionLocal

        db = SessionLocal()
        try:
            scenario_data = {
                "stock_code": stock_code,
                "operation": "stop_loss",
                "reason": reason,
                "holding_days": holding_days,
            }
            scenario_hash = hashlib.sha256(
                json.dumps(scenario_data, sort_keys=True).encode()
            ).hexdigest()[:16]

            existing = db.query(Experiences).filter(
                Experiences.scenario_hash == scenario_hash
            ).first()
            if existing:
                logger.info(f"经验已存在，跳过: {scenario_hash}")
                return

            abs_loss = abs(pnl_pct)
            confidence = min(90.0, 50.0 + abs_loss * 2)

            exp = Experiences(
                market_state="unknown",
                stock_code=stock_code,
                operation="stop_loss",
                operation_detail={
                    "trigger_price": trigger_price,
                    "cost_price": cost_price,
                    "reason": reason,
                },
                result="loss",
                pnl_pct=Decimal(str(round(pnl_pct, 2))),
                holding_days=holding_days,
                score=Decimal(str(round(max(0, 100 - abs_loss * 5), 2))),
                confidence=Decimal(str(round(confidence, 2))),
                tags=["止损", f"亏损{abs_loss:.1f}%", "auto"],
                scenario_hash=scenario_hash,
                source="real",
            )
            db.add(exp)
            db.commit()
            logger.info(f"止损经验已归档: {stock_code} pnl={pnl_pct:.2f}%")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"经验归档失败 {stock_code}: {e}")


def archive_trade_experience(
    stock_code: str,
    operation: str,
    pnl_pct: float,
    entry_price: float,
    exit_price: float | None,
    holding_days: int,
    strategy_type: str,
    reason: str,
):
    """交易完成时归档经验"""
    try:
        from src.db.models import Experiences
        from src.db.session import SessionLocal

        result = "profit" if pnl_pct > 0 else "loss"

        scenario_data = {
            "stock_code": stock_code,
            "operation": operation,
            "strategy_type": strategy_type,
            "pnl_sign": "profit" if pnl_pct > 0 else "loss",
        }
        scenario_hash = hashlib.sha256(
            json.dumps(scenario_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        db = SessionLocal()
        try:
            existing = db.query(Experiences).filter(
                Experiences.scenario_hash == scenario_hash
            ).first()
            if existing:
                logger.info(f"经验已存在，跳过: {scenario_hash}")
                return

            abs_pnl = abs(pnl_pct)
            confidence = min(90.0, 50.0 + abs_pnl * 2)
            score = 100 - abs_pnl * 5 if pnl_pct < 0 else 50 + abs_pnl * 3
            score = max(0, min(100, score))

            exp = Experiences(
                market_state="unknown",
                stock_code=stock_code,
                strategy_type=strategy_type,
                operation=operation,
                operation_detail={
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "reason": reason,
                    "holding_days": holding_days,
                },
                result=result,
                pnl_pct=Decimal(str(round(pnl_pct, 2))),
                holding_days=holding_days,
                score=Decimal(str(round(score, 2))),
                confidence=Decimal(str(round(confidence, 2))),
                tags=[result, operation, strategy_type],
                scenario_hash=scenario_hash,
                source="real",
            )
            db.add(exp)
            db.commit()
            logger.info(f"交易经验已归档: {stock_code} {operation} pnl={pnl_pct:.2f}%")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"交易经验归档失败 {stock_code}: {e}")


# ═══════════════════════════════════════════════════════════════════
# 微信推送（simplified）
# ═══════════════════════════════════════════════════════════════════

def send_wechat_notification(title: str, content: str) -> bool:
    """通过通知表发送微信推送"""
    try:
        from src.notification.wechat import get_notifier
        notifier = get_notifier()
        notifier.send(
            event_type="system",
            title=title,
            content=f"{title}\n{content}",
            priority="normal",
        )
        return True
    except Exception as e:
        logger.warning(f"微信推送异常: {e}")
        return False


def notify_stop_loss(stock_code: str, pnl_pct: float, reason: str):
    """止损触发通知"""
    send_wechat_notification(
        f"⚠️ 止损触发: {stock_code}",
        f"浮亏: {pnl_pct:.2f}%\n原因: {reason}"
    )


def notify_collect_news(new_count: int):
    """新闻采集完成通知"""
    if new_count > 0:
        send_wechat_notification(
            "📰 新闻采集",
            f"新增 {new_count} 条热点新闻"
        )


# ═══════════════════════════════════════════════════════════════════
# 定时任务：新闻采集
# ═══════════════════════════════════════════════════════════════════

def run_news_collection():
    """执行新闻采集并通知"""
    logger.info("[schedule] 开始新闻采集...")
    count = collect_hot_news()
    logger.info(f"[schedule] 新闻采集完成: 新增 {count} 条")
    if count > 0:
        notify_collect_news(count)
    return count


# ═══════════════════════════════════════════════════════════════════
# 定时任务：增强版止损监视器
# ═══════════════════════════════════════════════════════════════════

class EnhancedStopLossMonitor(StopLossMonitor):
    """增强版：止损触发后归档经验 + 推送通知"""

    def _execute_stop_loss(self, db, pos, sl_cond, current_price, pnl_pct, reason):
        super()._execute_stop_loss(db, pos, sl_cond, current_price, pnl_pct, reason)

        try:
            archive_stop_loss_experience(
                stock_code=pos.stock_code,
                pnl_pct=float(pnl_pct),
                trigger_price=float(current_price),
                cost_price=float(pos.cost_price),
                reason=reason,
            )
        except Exception as e:
            logger.error(f"止损经验归档异常: {e}")

        try:
            notify_stop_loss(pos.stock_code, float(pnl_pct), reason)
        except Exception as e:
            logger.error(f"止损推送异常: {e}")


def run_enhanced_stop_loss_monitor(scan_interval: int = 30):
    """运行增强版止损监视器"""
    monitor = EnhancedStopLossMonitor(scan_interval=scan_interval)
    monitor.start()


# ═══════════════════════════════════════════════════════════════════
# 定时任务：数据质量检查
# ═══════════════════════════════════════════════════════════════════

def run_data_quality_check():
    """执行数据质量检查（使用 SQLAlchemy）"""
    logger.info("[schedule] 开始数据质量检查...")
    try:
        db = get_session()
        try:
            result = db.execute(text("""
                SELECT stock_code, max(trade_date) as last_date
                FROM daily_klines
                GROUP BY stock_code
                ORDER BY last_date ASC
                LIMIT 10
            """))
            for code, last_date in result.fetchall():
                logger.warning(f"数据可能断更: {code} 最后数据 {last_date}")

            suspensions = detect_suspension(lookback_days=5)
            if suspensions:
                logger.warning(f"发现 {len(suspensions)} 个疑似停牌标的")
                for s in suspensions[:5]:
                    logger.warning(f"  停牌: {s.stock_code} {s.message}")

            result = db.execute(text("""
                SELECT p.stock_code, p.total_volume,
                       MAX(d.trade_date) as last_kline_date
                FROM positions p
                LEFT JOIN daily_klines d ON d.stock_code = p.stock_code
                WHERE p.total_volume > 0
                GROUP BY p.stock_code, p.total_volume
            """))
            for code, vol, last_date in result.fetchall():
                if last_date and last_date < date.today() - timedelta(days=3):
                    logger.warning(f"持仓 {code} 数据已断更 {last_date} 天")

            logger.info("[schedule] 数据质量检查完成")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"数据质量检查失败: {e}")


# ═══════════════════════════════════════════════════════════════════
# 定时任务：开盘前复核
# ═══════════════════════════════════════════════════════════════════

def run_pre_market_review():
    """开盘前复核（PRD 4.2.2节）"""
    logger.info("[schedule] 开盘前复核...")
    try:
        db = get_session()
        try:
            decisions = db.execute(text("""
                SELECT stock_code, final_decision, final_score, strategy_type
                FROM stock_pool
                WHERE date = (SELECT MAX(date) FROM stock_pool)
                AND final_decision = 'buy'
                ORDER BY final_score DESC
                LIMIT 5
            """)).fetchall()

            if not decisions:
                logger.info("[schedule] 无待执行决策")
                return

            cancelled = []
            for d in decisions:
                code = d[0]
                has_kline = db.execute(text("""
                    SELECT COUNT(*) FROM daily_klines
                    WHERE stock_code = :code
                    AND trade_date = (SELECT MAX(trade_date) FROM daily_klines WHERE stock_code = :code)
                """), {"code": code}).scalar()
                if not has_kline or has_kline == 0:
                    cancelled.append(code)
                    logger.warning(f"开盘前复核取消: {code} 可能停牌")

            if cancelled:
                msg = f"计划买入 {len(decisions)} 只，取消 {len(cancelled)} 只（{', '.join(cancelled)}）"
            else:
                msg = f"计划买入 {len(decisions)} 只，全部正常"

            send_wechat_notification("📋 开盘前复核", msg)
            logger.info(f"[schedule] {msg}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"开盘前复核失败: {e}")


# ═══════════════════════════════════════════════════════════════════
# 主调度器
# ═══════════════════════════════════════════════════════════════════

class Scheduler:
    """统一调度器"""

    def __init__(self):
        self._running = False
        self._last_news_time = 0.0
        self._last_data_quality_time = 0.0
        self._last_pre_market_time = 0.0

    def start(self):
        self._running = True
        logger.info("=" * 50)
        logger.info("FraxVerse 统一调度器启动")
        logger.info(f"  新闻采集: 每 {NEWS_INTERVAL}s")
        logger.info(f"  止损监视: 每 {STOP_LOSS_INTERVAL}s")
        logger.info(f"  数据质量: 每 {DATA_QUALITY_INTERVAL}s")
        logger.info(f"  开盘复核: 每 {PRE_MARKET_INTERVAL}s")
        logger.info("=" * 50)

        import threading
        sl_thread = threading.Thread(
            target=run_enhanced_stop_loss_monitor,
            args=(STOP_LOSS_INTERVAL,),
            daemon=True,
        )
        sl_thread.start()
        logger.info(f"止损监视器线程: {sl_thread.name}")

        while self._running:
            try:
                now = time.time()

                if now - self._last_news_time >= NEWS_INTERVAL:
                    self._last_news_time = now
                    run_news_collection()

                if now - self._last_data_quality_time >= DATA_QUALITY_INTERVAL:
                    self._last_data_quality_time = now
                    run_data_quality_check()

                if now - self._last_pre_market_time >= PRE_MARKET_INTERVAL:
                    current_hour = datetime.now(UTC).astimezone().hour
                    if 8 <= current_hour <= 10:
                        self._last_pre_market_time = now
                        run_pre_market_review()

                time.sleep(10)
            except KeyboardInterrupt:
                logger.info("收到中断信号")
                self.stop()
            except Exception as e:
                logger.error(f"调度循环异常: {e}", exc_info=True)
                time.sleep(30)

    def stop(self):
        self._running = False
        logger.info("调度器已停止")


# ═══════════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FraxVerse 统一调度器")
    parser.add_argument("--mode", type=str, default="all", choices=["all", "news", "stop-loss", "data-quality"])
    parser.add_argument("--once", type=str, default=None, choices=["news", "data-quality", "pre-market"])
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.once == "news":
        run_news_collection()
        return
    elif args.once == "data-quality":
        run_data_quality_check()
        return
    elif args.once == "pre-market":
        run_pre_market_review()
        return

    if args.mode == "news":
        while True:
            try:
                run_news_collection()
                time.sleep(NEWS_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"新闻采集异常: {e}")
                time.sleep(60)
    elif args.mode == "stop-loss":
        run_enhanced_stop_loss_monitor(STOP_LOSS_INTERVAL)
    elif args.mode == "data-quality":
        while True:
            try:
                run_data_quality_check()
                time.sleep(DATA_QUALITY_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"数据质量异常: {e}")
                time.sleep(60)
    else:
        scheduler = Scheduler()
        try:
            signal.signal(signal.SIGINT, lambda s, f: scheduler.stop())
            signal.signal(signal.SIGTERM, lambda s, f: scheduler.stop())
        except ValueError:
            pass
        scheduler.start()


if __name__ == "__main__":
    main()
