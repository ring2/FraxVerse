"""市场状态自动机

P0-5.1: 市场状态定义与切换

四种市场状态 + 观望态（震荡保护触发）:
- 非主线状态 (NO_MAINLINE) — 仓位0%，无明确方向
- 底部机会期 (BOTTOM_OPPORTUNITY) — 策略一适用
- 主线确认 (MAINLINE_CONFIRMED) — 策略二适用
- 趋势上升期 (TREND_UPTREND) — 策略二适用
- 观望态 (WATCH) — 震荡保护触发，仓位0%

状态转换规则（DD-03 §3.1）:
1. 非主线状态 → 主线确认（检测到主线板块）
2. 非主线状态 → 底部机会期（无主线+底部信号）
3. 主线确认 → 趋势上升期（趋势特征确认）
4. 主线确认 → 非主线状态（主线消失）
5. 趋势上升期 → 主线确认（趋势破坏但主线还在）
6. 趋势上升期 → 非主线状态（趋势破坏+主线消失）
7. 底部机会期 → 趋势上升期（趋势启动）
8. 底部机会期 → 非主线状态（底部信号消失）
9. 观望态 → 非主线状态（3天冷确后无震荡）
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── 市场状态枚举 ──────────────────────────────────────────────

class MarketState(StrEnum):
    BOTTOM_OPPORTUNITY = "底部机会期"
    MAINLINE_CONFIRMED = "主线确认"
    TREND_UPTREND = "趋势上升期"
    NO_MAINLINE = "非主线状态"
    WATCH = "观望态"


# ── 信号数据类 ─────────────────────────────────────────────────

@dataclass
class BottomSignal:
    detected: bool = False
    count: int = 0


# ── 状态转换引擎 ───────────────────────────────────────────────

class StateMachine:
    """市场状态自动机 — 幂等性：否（状态切换有副作用）

    每次调用 determine_market_state 可能改变内部状态并记录日志。
    """

    # 配置常量（DD-03 §2.1.3 strategy_params）
    COOLDOWN_DAYS: int = 3              # 状态切换冷却期
    OSCILLATION_THRESHOLD: int = 3      # 震荡保护阈值（3天内切换次数）
    OSCILLATION_WINDOW: int = 3         # 震荡检测窗口（天）
    MAX_MAINLINES: int = 2               # 最大主线并行数
    BOTTOM_COUNT_THRESHOLD: int = 50    # 底部特征股票数量阈值

    def __init__(self) -> None:
        self.current_state: MarketState = MarketState.NO_MAINLINE
        self._log: list[dict[str, Any]] = []  # 内存日志（P0不依赖DB）
        self._last_switch_date: date | None = None

    def determine_market_state(
        self,
        trade_date: date,
        mainline_sectors: list[str] | None = None,
        bottom_detected: bool = False,
        bottom_count: int = 0,
        trend_confirmed: bool = False,
        trend_broken: bool = False,
        trend_starting: bool = False,
    ) -> MarketState:
        """确定市场状态（DD-03 §3.1 determine_market_state）

        Args:
            trade_date: 当前交易日
            mainline_sectors: 检测到的主线板块列表
            bottom_detected: 是否检测到底部信号
            bottom_count: 底部特征股票数量
            trend_confirmed: 趋势是否确认
            trend_broken: 趋势是否被破坏
            trend_starting: 趋势是否启动
        """
        current = self.current_state
        mainline_sectors = mainline_sectors or []

        # 1. 冷却期检查
        if self._last_switch_date is not None:
            days_since_switch = (trade_date - self._last_switch_date).days
            if days_since_switch < self.COOLDOWN_DAYS:
                logger.info(
                    "状态冷却期内，保持当前状态 %s（还剩%d天）",
                    current.value, self.COOLDOWN_DAYS - days_since_switch,
                )
                return current

        # 2. 震荡保护检测
        recent_switch_count = self._count_recent_switches(trade_date)
        if recent_switch_count >= self.OSCILLATION_THRESHOLD:
            new_state = MarketState.WATCH
            if new_state != current:
                self._switch_state(
                    trade_date, current, new_state,
                    f"震荡保护：{recent_switch_count}天内切换{recent_switch_count}次",
                    mainline_sectors=mainline_sectors,
                )
            return new_state

        # 3. 状态转换逻辑
        new_state = self._transition(
            current,
            mainline_sectors=mainline_sectors,
            bottom_detected=bottom_detected,
            trend_confirmed=trend_confirmed,
            trend_broken=trend_broken,
            trend_starting=trend_starting,
            recent_switch_count=recent_switch_count,
        )

        # 4. 记录状态切换
        if new_state != current:
            self._switch_state(
                trade_date, current, new_state,
                self._build_reason(current, new_state, mainline_sectors,
                                   bottom_detected, trend_confirmed, trend_broken, trend_starting),
                mainline_sectors=mainline_sectors,
            )

        return new_state

    def _transition(
        self,
        current: MarketState,
        *,
        mainline_sectors: list[str],
        bottom_detected: bool,
        trend_confirmed: bool,
        trend_broken: bool,
        trend_starting: bool,
        recent_switch_count: int = 0,
    ) -> MarketState:
        """状态转换逻辑（DD-03 §3.1 switch case）"""
        new_state = current  # 默认保持

        if current == MarketState.NO_MAINLINE:
            if len(mainline_sectors) > 0:
                new_state = MarketState.MAINLINE_CONFIRMED
            elif bottom_detected:
                new_state = MarketState.BOTTOM_OPPORTUNITY

        elif current == MarketState.MAINLINE_CONFIRMED:
            if trend_confirmed:
                new_state = MarketState.TREND_UPTREND
            elif len(mainline_sectors) == 0:
                new_state = MarketState.NO_MAINLINE

        elif current == MarketState.TREND_UPTREND:
            if trend_broken:
                new_state = MarketState.MAINLINE_CONFIRMED
                if len(mainline_sectors) == 0:
                    new_state = MarketState.NO_MAINLINE

        elif current == MarketState.BOTTOM_OPPORTUNITY:
            if trend_starting:
                new_state = MarketState.TREND_UPTREND
            elif not bottom_detected:
                new_state = MarketState.NO_MAINLINE

        elif current == MarketState.WATCH and recent_switch_count == 0:
            new_state = MarketState.NO_MAINLINE

        return new_state

    def _switch_state(
        self,
        trade_date: date,
        from_state: MarketState,
        to_state: MarketState,
        reason: str,
        mainline_sectors: list[str] | None = None,
    ) -> None:
        """执行状态切换并记录日志"""
        self.current_state = to_state
        self._last_switch_date = trade_date
        log_state_change(
            trade_date=trade_date,
            from_state=from_state.value,
            to_state=to_state.value,
            trigger_reason=reason,
            main_line_sector=mainline_sectors[0] if mainline_sectors else None,
            confidence=self._calculate_confidence(from_state, to_state),
        )

    def _count_recent_switches(self, trade_date: date) -> int:
        """统计最近N天内的状态切换次数"""
        cutoff = trade_date - timedelta(days=self.OSCILLATION_WINDOW)
        count = 0
        for entry in self._log:
            if entry.get("trade_date", date.min) >= cutoff:
                count += 1
        return count

    def _calculate_confidence(self, from_state: MarketState, to_state: MarketState) -> float:
        """计算状态切换信心分（简化版）"""
        # 从非主线→主线确认有较高信心
        if from_state == MarketState.NO_MAINLINE and to_state == MarketState.MAINLINE_CONFIRMED:
            return 0.8
        # 从主线确认→趋势上升，信心较高
        if from_state == MarketState.MAINLINE_CONFIRMED and to_state == MarketState.TREND_UPTREND:
            return 0.85
        # 底部机会→趋势启动，信心中等
        if from_state == MarketState.BOTTOM_OPPORTUNITY and to_state == MarketState.TREND_UPTREND:
            return 0.7
        # 降级类切换（主线消失/趋势破坏），信心低
        if from_state in (MarketState.MAINLINE_CONFIRMED, MarketState.TREND_UPTREND) \
                and to_state == MarketState.NO_MAINLINE:
            return 0.4
        # 震荡保护触发，信心极低
        if to_state == MarketState.WATCH:
            return 0.2
        return 0.5

    def _build_reason(
        self,
        from_state: MarketState,
        to_state: MarketState,
        mainline_sectors: list[str],
        bottom_detected: bool,
        trend_confirmed: bool,
        trend_broken: bool,
        trend_starting: bool,
    ) -> str:
        """构建状态切换原因"""
        parts: list[str] = []
        if mainline_sectors:
            parts.append(f"主线板块:{','.join(mainline_sectors)}")
        if bottom_detected:
            parts.append("底部信号")
        if trend_confirmed:
            parts.append("趋势确认")
        if trend_broken:
            parts.append("趋势破坏")
        if trend_starting:
            parts.append("趋势启动")
        reason = f"{from_state.value}→{to_state.value}"
        if parts:
            reason += f" ({','.join(parts)})"
        return reason


# ── 核心检测函数 ───────────────────────────────────────────────

def detect_mainline_sectors() -> list[str]:
    """检测主线板块（DD-03 §3.1）

    P0版：返回空列表占位，后续对接DB查询。
    查询板块数据：资金集中度>=12% 且 连续2天。
    最多取2条主线。
    """
    # P0占位 — 等待sector_data数据可用
    logger.info("检测主线板块...（P0占位）")
    return []


def detect_bottom_signals() -> BottomSignal:
    """检测底部信号（DD-03 §3.1）

    P0版：返回未检测到底部信号，后续对接DB查询。
    查询60日跌幅≥20%且5日内有单日跌幅≥5%的股票数 ≥ 50只。
    """
    # P0占位 — 等待daily_klines数据可用
    logger.info("检测底部信号...（P0占位）")
    return BottomSignal(detected=False, count=0)


def log_state_change(
    trade_date: date,
    from_state: str,
    to_state: str,
    trigger_reason: str,
    main_line_sector: str | None = None,
    confidence: float = 0.5,
) -> None:
    """记录状态切换日志（DD-03 §3.1 log_state_change）

    P0版：内存日志 + logger。
    完整版：INSERT INTO market_state_log + 发布MQ事件。
    """
    logger.info(
        "市场状态切换: %s → %s | 原因: %s | 主线: %s | 信心: %.2f",
        from_state, to_state, trigger_reason,
        main_line_sector or "无", confidence,
    )
    # P0暂不写入DB，后续由调度器统一入库
