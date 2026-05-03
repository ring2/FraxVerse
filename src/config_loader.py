"""
FraxVerse · 热配置读取模块

替代各模块中的硬编码常量，从 SystemConfig 表运行时读取。
所有函数都接受 db: Session 参数，在同一个事务内批量查询。

用法:
    from src.config_loader import (
        load_strategy_config, load_scorer_weights,
        load_trade_config, load_agent_config,
        load_risk_config, load_backtest_config,
    )
"""
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from src.db.models import SystemConfig

# ─── 内部：批量加载配置 ─────────────────────────────────────────────


def _load_configs(db: Session) -> dict[str, Any]:
    """从 SystemConfig 表加载全部配置并转换类型"""
    rows = db.query(SystemConfig).all()
    result: dict[str, Any] = {}
    for row in rows:
        if row.config_type == "bool":
            result[row.config_key] = row.config_value.lower() == "true"
        elif row.config_type == "number":
            try:
                result[row.config_key] = int(row.config_value) if "." not in row.config_value else float(row.config_value)
            except (ValueError, TypeError):
                result[row.config_key] = row.config_value
        else:
            result[row.config_key] = row.config_value
    return result


# ─── 各模块专用加载器 ──────────────────────────────────────────────


def load_scorer_weights(db: Session) -> dict[str, float]:
    """加载评分权重（对应 scorer.py WEIGHTS — 设计文档固定值）"""
    # 设计文档固定权重，前端的经验库权重配置不会影响评分权重
    # 后续如需让评分权重可配置，需在 settings 页面新增专用配置项
    return {
        "volume_price": 0.20,
        "fund": 0.25,
        "sentiment": 0.15,
        "mainforce": 0.25,
        "capital_logic": 0.15,
    }


def load_strategy_config(db: Session) -> dict[str, Any]:
    """加载策略筛选参数（对应 screener.py 常量）"""
    cfg = _load_configs(db)
    return {
        "drop_60d_threshold": float(cfg.get("strategy_bottom_decline_pct", 20)),
        "drop_5d_threshold": float(cfg.get("strategy_bottom_crash_pct", 5)) * -1,  # 转为负值
        "min_market_cap": 5_000_000_000,
        "max_market_cap": 50_000_000_000,
        "min_daily_amount": 100_000_000,
        "min_days_listed": 180,
        "sector_concentration": float(cfg.get("strategy_sector_concentration", 12)),
        "min_adx": float(cfg.get("strategy_adx_threshold", 25)),
        "volume_ratio": float(cfg.get("strategy_shrink_ratio", 80)) / 100,
        "bottom_check_days": int(cfg.get("strategy_bottom_days", 60)),
        "price_drop_threshold_s2": float(cfg.get("strategy_momentum_drop_pct", 3)) * -1,  # 转为负值
        "min_daily_amount_s2": int(cfg.get("strategy_momentum_min_amount", 300_000_000)),
        "min_klines_s2": int(cfg.get("strategy_momentum_min_klines", 66)),
        "sector_check_days": int(cfg.get("strategy_sector_check_days", 2)),
        "min_klines_s1": int(cfg.get("strategy_bottom_min_klines", 30)),
    }


def load_trade_config(db: Session) -> dict[str, Any]:
    """加载交易配置（对应 engine.py 常量）"""
    cfg = _load_configs(db)
    max_pos = int(cfg.get("strategy_max_positions", 3))
    return {
        "max_positions": max_pos,
        "max_risk_per_stock_pct": Decimal("1.5"),
        "flat_avg_threshold_pct": Decimal("-0.5"),
        "stop_loss_cooldown_hours": 24,
        "stop_profit_cooldown_hours": 12,
        "commission_rate": Decimal(str(cfg.get("trade_commission_rate", 3))) / Decimal("10000"),  # 万分之 → decimal
        "stamp_tax_rate": Decimal(str(cfg.get("trade_stamp_tax_rate", 1))) / Decimal("1000"),  # 千分之 → decimal
        "slippage": int(cfg.get("trade_slippage", 1)),
        "stop_profit_tiers": [
            {"stage": "first_take", "trigger_pct": Decimal(cfg.get("strategy_take_profit_pct", 10)), "sell_pct": Decimal("30")},
            {"stage": "second_take", "trigger_pct": Decimal(str(float(cfg.get("strategy_take_profit_pct", 10)) * 2)), "sell_pct": Decimal("40")},
            {"stage": "trailing", "trigger_pct": Decimal(str(float(cfg.get("strategy_take_profit_pct", 10)) * 1.5)), "sell_pct": Decimal("50")},
        ],
    }


def load_backtest_config(db: Session, strategy_num: int = 1) -> dict[str, Any]:
    """加载回测参数（对应 backtest_runner.py 常量）"""
    cfg = _load_configs(db)
    return {
        "score_threshold": 55.0,
        "stop_loss_pct": float(cfg.get("strategy_stop_loss_pct", 5)),
        "stop_profit_pct": float(cfg.get("strategy_take_profit_pct", 10)),
        "position_pct": 20.0 if strategy_num == 1 else 25.0,
    }


def load_agent_config(db: Session) -> dict[str, Any]:
    """加载 Agent 配置（对应 llm_client.py 超时/轮数）"""
    cfg = _load_configs(db)
    return {
        "timeout": int(cfg.get("llm_timeout", 60)),
        "max_retries": 2,
        "discussion_rounds": int(cfg.get("agent_discussion_rounds", 2)),
        "max_concurrent": int(cfg.get("llm_max_concurrent", 8)),
    }


def load_risk_config(db: Session) -> dict[str, Any]:
    """加载风控配置（对应前端风控参数）"""
    cfg = _load_configs(db)
    return {
        "daily_max_drawdown": float(cfg.get("risk_daily_max_drawdown", 5)),
        "extreme_drawdown": float(cfg.get("risk_extreme_drawdown", 8)),
        "max_consecutive_losses": int(cfg.get("risk_max_consecutive_losses", 5)),
        "single_position_limit": float(cfg.get("risk_single_position_limit", 30)),
        "factor_crowding": float(cfg.get("risk_factor_crowding", 48)),
        "extreme_market_decline": float(cfg.get("risk_extreme_market_decline", 5)),
    }
