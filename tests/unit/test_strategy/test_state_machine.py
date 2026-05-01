"""测试 P0-5.1 市场状态自动机

DD-03 §2.2 & §3.1 完整验证：
- 5种市场状态枚举
- StateMachine 状态转换规则（9条转换路径）
- 冷却期保护
- 震荡保护
- 初始状态、空日志、边界条件
"""

from datetime import date, timedelta

from src.strategy.state_machine import (
    MarketState,
    StateMachine,
    log_state_change,
)

# ── 辅助 ────────────────────────────────────────────────────────

_BASE = date(2026, 5, 12)


def _call(
    sm: StateMachine,
    trade_date: date = _BASE,
    mainline_sectors: list[str] | None = None,
    bottom_detected: bool = False,
    trend_confirmed: bool = False,
    trend_broken: bool = False,
    trend_starting: bool = False,
) -> MarketState:
    return sm.determine_market_state(
        trade_date=trade_date,
        mainline_sectors=mainline_sectors,
        bottom_detected=bottom_detected,
        trend_confirmed=trend_confirmed,
        trend_broken=trend_broken,
        trend_starting=trend_starting,
    )


# ════════════════════════════════════════════════════════════════
# MarketState 枚举
# ════════════════════════════════════════════════════════════════

class TestMarketState:

    def test_five_states(self):
        assert len(MarketState) == 5

    def test_values(self):
        assert MarketState.BOTTOM_OPPORTUNITY.value == "底部机会期"
        assert MarketState.MAINLINE_CONFIRMED.value == "主线确认"
        assert MarketState.TREND_UPTREND.value == "趋势上升期"
        assert MarketState.NO_MAINLINE.value == "非主线状态"
        assert MarketState.WATCH.value == "观望态"


# ════════════════════════════════════════════════════════════════
# 初始状态
# ════════════════════════════════════════════════════════════════

class TestInitialState:

    def test_default_is_no_mainline(self):
        assert StateMachine().current_state == MarketState.NO_MAINLINE

    def test_no_switch_without_signals(self):
        """场景：无主线+无底部信号 → 保持非主线状态"""
        sm = StateMachine()
        assert _call(sm) == MarketState.NO_MAINLINE

    def test_switch_to_mainline_with_signals(self):
        """场景：检测到主线 → 切换为主线确认"""
        sm = StateMachine()
        result = _call(sm, mainline_sectors=["半导体"])
        assert result == MarketState.MAINLINE_CONFIRMED
        assert sm.current_state == MarketState.MAINLINE_CONFIRMED

    def test_switch_to_bottom_without_mainline(self):
        """场景：无主线但有底部信号 → 切换为底部机会期"""
        sm = StateMachine()
        result = _call(sm, bottom_detected=True)
        assert result == MarketState.BOTTOM_OPPORTUNITY


# ════════════════════════════════════════════════════════════════
# 冷却期
# ════════════════════════════════════════════════════════════════

class TestCooldown:

    def test_cooldown_prevents_immediate_switch(self):
        """场景：刚切换状态 → 冷却期内不能再次切换"""
        sm = StateMachine()
        _call(sm, trade_date=_BASE, mainline_sectors=["半导体"])  # → MAINLINE_CONFIRMED
        sm._last_switch_date = _BASE  # 强制最近切换日期

        # 第2天冷却期内，尝试切换到趋势上升期
        result = _call(sm, trade_date=_BASE + timedelta(days=1), trend_confirmed=True)
        assert result == MarketState.MAINLINE_CONFIRMED  # 冷却期内保持

    def test_cooldown_expired_allows_switch(self):
        """场景：冷却期3天过后 → 允许切换"""
        sm = StateMachine()
        _call(sm, trade_date=_BASE, mainline_sectors=["半导体"])  # → MAINLINE_CONFIRMED
        sm._last_switch_date = _BASE

        # 第4天（超过冷却期），趋势确认 → TREND_UPTREND
        result = _call(sm, trade_date=_BASE + timedelta(days=4), trend_confirmed=True)
        assert result == MarketState.TREND_UPTREND

    def test_initial_no_cooldown_applies(self):
        """场景：首次调用（无切换日志）→ 不触发冷却"""
        sm = StateMachine()
        result = _call(sm, bottom_detected=True)
        assert result == MarketState.BOTTOM_OPPORTUNITY


# ════════════════════════════════════════════════════════════════
# 震荡保护
# ════════════════════════════════════════════════════════════════

class TestOscillationProtection:

    def test_oscillation_triggers_watch(self):
        """场景：3天内切换3次 → 进入观望态"""
        sm = StateMachine()
        # 快速模拟3次切换
        sm._log = [
            {"trade_date": _BASE - timedelta(days=2)},
            {"trade_date": _BASE - timedelta(days=1)},
            {"trade_date": _BASE},
        ]
        result = _call(sm)
        assert result == MarketState.WATCH

    def test_no_oscillation_normal(self):
        """场景：只有1次切换 → 正常运行"""
        sm = StateMachine()
        sm._log = [
            {"trade_date": _BASE - timedelta(days=3)},
        ]
        result = _call(sm, bottom_detected=True)
        assert result == MarketState.BOTTOM_OPPORTUNITY


# ════════════════════════════════════════════════════════════════
# 状态转换（完整9条路径）
# ════════════════════════════════════════════════════════════════

class TestStateTransitions:

    def test_no_mainline_to_mainline(self):
        """1. 非主线状态→主线确认：检测到主线"""
        sm = StateMachine()
        sm.current_state = MarketState.NO_MAINLINE
        assert _call(sm, mainline_sectors=["半导体"]) == MarketState.MAINLINE_CONFIRMED

    def test_no_mainline_to_bottom(self):
        """2. 非主线状态→底部机会期：无主线+底部信号"""
        sm = StateMachine()
        sm.current_state = MarketState.NO_MAINLINE
        assert _call(sm, bottom_detected=True) == MarketState.BOTTOM_OPPORTUNITY

    def test_no_mainline_stays(self):
        """3. 非主线状态→非主线状态：无主线+无底部"""
        sm = StateMachine()
        sm.current_state = MarketState.NO_MAINLINE
        assert _call(sm) == MarketState.NO_MAINLINE

    def test_mainline_to_trend(self):
        """4. 主线确认→趋势上升期：趋势确认"""
        sm = StateMachine()
        sm.current_state = MarketState.MAINLINE_CONFIRMED
        assert _call(sm, trend_confirmed=True) == MarketState.TREND_UPTREND

    def test_mainline_to_no_mainline(self):
        """5. 主线确认→非主线状态：主线消失"""
        sm = StateMachine()
        sm.current_state = MarketState.MAINLINE_CONFIRMED
        assert _call(sm) == MarketState.NO_MAINLINE

    def test_trend_to_mainline(self):
        """6. 趋势上升期→主线确认：趋势破坏但主线还在"""
        sm = StateMachine()
        sm.current_state = MarketState.TREND_UPTREND
        assert _call(sm, mainline_sectors=["半导体"], trend_broken=True) == MarketState.MAINLINE_CONFIRMED

    def test_trend_to_no_mainline(self):
        """7. 趋势上升期→非主线状态：趋势破坏+主线消失"""
        sm = StateMachine()
        sm.current_state = MarketState.TREND_UPTREND
        assert _call(sm, trend_broken=True) == MarketState.NO_MAINLINE

    def test_trend_stays(self):
        """8. 趋势上升期→趋势上升期：趋势未破坏"""
        sm = StateMachine()
        sm.current_state = MarketState.TREND_UPTREND
        assert _call(sm, mainline_sectors=["半导体"]) == MarketState.TREND_UPTREND

    def test_bottom_to_trend(self):
        """9. 底部机会期→趋势上升期：趋势启动"""
        sm = StateMachine()
        sm.current_state = MarketState.BOTTOM_OPPORTUNITY
        assert _call(sm, trend_starting=True) == MarketState.TREND_UPTREND

    def test_bottom_to_no_mainline(self):
        """10. 底部机会期→非主线状态：底部信号消失"""
        sm = StateMachine()
        sm.current_state = MarketState.BOTTOM_OPPORTUNITY
        assert _call(sm) == MarketState.NO_MAINLINE

    def test_bottom_stays(self):
        """11. 底部机会期→底部机会期：底部信号持续"""
        sm = StateMachine()
        sm.current_state = MarketState.BOTTOM_OPPORTUNITY
        assert _call(sm, bottom_detected=True) == MarketState.BOTTOM_OPPORTUNITY

    def test_watch_to_no_mainline(self):
        """12. 观望态→非主线状态：无震荡"""
        sm = StateMachine()
        sm.current_state = MarketState.WATCH
        assert _call(sm) == MarketState.NO_MAINLINE

    def test_watch_stays(self):
        """13. 观望态→观望态：震荡仍在"""
        sm = StateMachine()
        sm.current_state = MarketState.WATCH
        sm._log = [{"trade_date": _BASE - timedelta(days=1)}]
        assert _call(sm) == MarketState.WATCH


# ════════════════════════════════════════════════════════════════
# 边界条件
# ════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_mainline_priority_over_bottom(self):
        """场景：同时有主线和底部信号 → 主线优先"""
        sm = StateMachine()
        result = _call(sm, mainline_sectors=["半导体"], bottom_detected=True)
        assert result == MarketState.MAINLINE_CONFIRMED  # 不是底部机会期

    def test_multiple_mainline_sectors(self):
        """场景：多条主线 → 正常允许"""
        sm = StateMachine()
        result = _call(sm, mainline_sectors=["半导体", "军工", "AI"])
        assert result == MarketState.MAINLINE_CONFIRMED

    def test_log_state_change_output(self):
        """验证：log_state_change 不抛出异常"""
        log_state_change(
            trade_date=_BASE,
            from_state="测试",
            to_state="测试",
            trigger_reason="单元测试",
        )
        # 只验证不抛异常
