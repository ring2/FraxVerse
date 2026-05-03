"""FraxVerse 回测引擎 — 基于 backtesting 库的轻量回测框架

设计原则：
- 替代 vnpy BacktestingEngine：去除 PyQt/PySide/Polars/Plotly 依赖
- 保留组合回测思想：portfolio-level 的粗筛→评分→选股回测
- A股规则内建：T+1、涨跌停10%、交易费率
- 两阶段实现：
  1. SignalBacktest：对单标的+决策信号列表进行回测（底层用 backtesting 库）
  2. PortfolioBacktester：按日运行完整策略流程，生成信号，聚合为组合绩效

对齐 DD-03 §4.4 PortfolioBacktester 伪代码设计（见开发实施计划 vnpy→backtesting 迁移说明）
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np  # noqa: I001
import pandas as pd

logger = logging.getLogger(__name__)

# ── A股规则常量 ──────────────────────────────────────────────────
T_PLUS_1 = True  # T+1 交易
LIMIT_UP_PCT = 0.10  # 涨停 10%
LIMIT_DOWN_PCT = -0.10  # 跌停 10%
COMMISSION_RATE = 0.0003  # 佣金万三（买入+卖出双向）
STAMP_TAX_RATE = 0.001  # 印花税千分之一（卖出单向）
SLIPPAGE_RATE = 0.001  # 滑点 0.1%
TRADE_UNIT = 100  # A股 1 手 = 100 股
MIN_HOLD_DAYS = 2  # 最小数据行数
ANNUAL_PCT = -100  # 年化计算保底


# ═══════════════════════════════════════════════════════════════════
# BacktestResult — 对齐 DD-03 §2.1.4 backtest_results 表
# ═══════════════════════════════════════════════════════════════════


@dataclass
class BacktestResult:
    """单标的回测结果，对齐 backtest_results 表字段"""

    strategy_type: str = ""
    start_date: date | None = None
    end_date: date | None = None
    initial_capital: float = 0.0
    final_capital: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    total_trades: int = 0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    params_used: dict = field(default_factory=dict)
    daily_equity: dict = field(default_factory=dict)

    def to_insert_dict(self) -> dict:
        """转为 backtest_results 表插入数据"""
        return {
            "strategy_type": self.strategy_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": round(self.initial_capital, 2),
            "final_capital": round(self.final_capital, 2),
            "annual_return": round(self.annual_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_loss_ratio": round(self.profit_loss_ratio, 4),
            "total_trades": self.total_trades,
            "params_used": json.dumps(self.params_used, default=str),
            "daily_equity": json.dumps(self.daily_equity, default=str),
        }


@dataclass
class PortfolioResult:
    """组合回测结果 — 多标的聚合绩效"""

    strategy_type: str = ""
    start_date: date | None = None
    end_date: date | None = None
    initial_capital: float = 0.0
    final_capital: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    total_trades: int = 0
    stock_count: int = 0
    daily_equity: dict = field(default_factory=dict)
    individual_results: dict[str, BacktestResult] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════
# TradeSignal — 交易信号
# ═══════════════════════════════════════════════════════════════════


@dataclass
class TradeSignal:
    """单日交易决策信号"""

    date: date
    action: str  # buy / hold / sell
    price: float = 0.0
    shares: int = 0  # 买入股数（A股需100的整数倍）
    position_pct: float = 0.0  # 建议仓位比例
    stop_loss: float = 0.0
    stop_profit: float = 0.0
    reason: str = ""


@dataclass
class TradeRecord:
    """一笔已完成的交易"""

    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    direction: str  # long
    pnl: float
    return_pct: float
    exit_reason: str = ""


# ═══════════════════════════════════════════════════════════════════
# BacktestingEngine — 主回测引擎类
# ═══════════════════════════════════════════════════════════════════


class BacktestingEngine:
    """FraxVerse 回测引擎

    替代 vnpy BacktestingEngine，使用 backtesting 库做底层计算。
    支持逐标的信号回测和组合回测。

    用法：
        engine = BacktestingEngine()
        engine.set_parameters(
            data=klines_df,
            start="2024-01-01",
            end="2024-12-31",
            capital=1000000,
            signals=[TradeSignal(...)],
        )
        result = engine.run()
    """

    def __init__(self):
        self._data: pd.DataFrame | None = None
        self._start: date | None = None
        self._end: date | None = None
        self._capital: float = 100000.0
        self._commission: float = COMMISSION_RATE
        self._slippage: float = SLIPPAGE_RATE
        self._stamp_tax: float = STAMP_TAX_RATE
        self._signals: list[TradeSignal] = []
        self._position: int = 0
        self._entry_price: float = 0.0
        self._entry_date: date | None = None
        self._trades: list[TradeRecord] = []
        self._daily_equity: dict = {}
        self._daily_nav: dict = {}
        self._result: BacktestResult | None = None

    @property
    def result(self) -> BacktestResult | None:
        return self._result

    def set_parameters(
        self,
        data: pd.DataFrame | None = None,
        start: str | date | None = None,
        end: str | date | None = None,
        capital: float = 100000.0,
        commission: float = COMMISSION_RATE,
        slippage: float = SLIPPAGE_RATE,
        stamp_tax: float = STAMP_TAX_RATE,
        signals: list[TradeSignal] | None = None,
    ) -> None:  # noqa: PLR0913
        """设置回测参数"""
        if data is not None:
            self._data = data.copy()
        if start is not None:
            self._start = pd.Timestamp(start).date() if not isinstance(start, date) else start
        if end is not None:
            self._end = pd.Timestamp(end).date() if not isinstance(end, date) else end
        self._capital = capital
        self._commission = commission
        self._slippage = slippage
        self._stamp_tax = stamp_tax
        if signals is not None:
            self._signals = signals

    def run(self) -> BacktestResult:
        """执行回测并返回结果"""
        if self._data is None or self._data.empty:
            return self._empty_result("数据为空")

        # 准备回测数据
        run_data = self._prepare_data()

        # 无信号时返回空结果
        if not self._signals:
            self._result = self._empty_result("无交易信号")
            return self._result

        # 按信号驱动回测
        self._run_with_signals(run_data)

        # 计算结果
        self._result = self._calculate_result()
        return self._result

    # ── 内部方法 ──────────────────────────────────────────────────

    def _prepare_data(self) -> pd.DataFrame:  # noqa: PLR0912
        """准备回测数据：过滤日期范围、添加技术字段"""
        data = self._data.copy()

        # 确保必要列存在
        col_map = {}
        for src_col in ["open", "Open", "OPEN"]:
            if src_col in data.columns:
                col_map[src_col] = "Open"
                break
        for src_col in ["high", "High", "HIGH"]:
            if src_col in data.columns:
                col_map[src_col] = "High"
                break
        for src_col in ["low", "Low", "LOW"]:
            if src_col in data.columns:
                col_map[src_col] = "Low"
                break
        for src_col in ["close", "Close", "CLOSE"]:
            if src_col in data.columns:
                col_map[src_col] = "Close"
                break
        for src_col in ["volume", "Volume", "VOLUME", "vol"]:
            if src_col in data.columns:
                col_map[src_col] = "Volume"
                break

        data = data.rename(columns=col_map)

        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"K线数据缺少必要列: {missing}")

        # 确保有日期列
        if "date" in data.columns:
            data["date"] = pd.to_datetime(data["date"])
        elif "datetime" in data.columns:
            data["date"] = pd.to_datetime(data["datetime"])
        elif "Date" in data.columns:
            data["date"] = pd.to_datetime(data["Date"])
        elif "Datetime" in data.columns:
            data["date"] = pd.to_datetime(data["Datetime"])
        else:
            data["date"] = data.index
            if not isinstance(data["date"].iloc[0], pd.Timestamp):
                raise ValueError("无法识别日期列，请提供 date/datetime 列或 DatetimeIndex")

        # 按日期过滤
        if self._start:
            data = data[data["date"] >= pd.Timestamp(self._start)].copy()
        if self._end:
            data = data[data["date"] <= pd.Timestamp(self._end)].copy()

        data = data.sort_values("date").reset_index(drop=True)

        return data

    def _run_with_signals(self, data: pd.DataFrame) -> None:  # noqa: PLR0912, PLR0915
        """按交易信号驱动回测（带T+1规则）"""
        if not self._signals:
            return

        # 将信号按日期建立索引
        signal_map: dict[date, TradeSignal] = {}
        for sig in self._signals:
            signal_map[sig.date] = sig

        cash = self._capital
        position = 0  # 持股数
        entry_price = 0.0
        entry_date: date | None = None
        transactions: list[TradeRecord] = []

        # 逐日模拟
        daily_equity: dict[str, float] = {}

        for _, row in data.iterrows():
            d = row["date"].date()
            close = float(row["Close"])
            high = float(row["High"])

            # 当前持仓市值
            hold_value = position * close
            equity = cash + hold_value
            daily_equity[d.isoformat()] = round(equity, 2)

            # 查找当日信号
            signal = signal_map.get(d)

            # 处理 T+1：当日买入信号 → 第二天才能卖出（过了T+1才允许卖）
            if signal and signal.action == "sell" and position > 0 and entry_date and (d - entry_date).days >= 1:# noqa: SIM102
                    # 卖出手续费
                    sell_value = position * close * (1 - self._slippage)
                    fee = sell_value * self._commission
                    stamp = sell_value * self._stamp_tax
                    revenue = sell_value - fee - stamp
                    pnl = revenue - position * entry_price

                    transactions.append(TradeRecord(
                        entry_date=entry_date,
                        exit_date=d,
                        entry_price=entry_price,
                        exit_price=close,
                        shares=position,
                        direction="long",
                        pnl=round(pnl, 2),
                        return_pct=round((close / entry_price - 1) * 100, 2),
                        exit_reason="signal",
                    ))

                    cash += revenue
                    position = 0
                    entry_price = 0.0
                    entry_date = None

            # 检查涨跌停（涨停不能买入）
            is_limit_up = False
            if "pre_close" in row:
                pre_close = float(row["pre_close"])
                is_limit_up = (close >= high) and (close >= pre_close * (1 + LIMIT_UP_PCT))

            # 买入信号
            if signal and signal.action == "buy" and position == 0 and not is_limit_up:
                # 计算买入数量（按建议仓位）
                if signal.position_pct > 0:
                    capital_alloc = self._capital * (signal.position_pct / 100.0)
                else:
                    capital_alloc = self._capital * 0.2
                buy_value = min(capital_alloc, cash)
                buy_price = close * (1 + self._slippage)  # 滑点：向上
                max_shares = int(buy_value / buy_price / TRADE_UNIT) * TRADE_UNIT

                if max_shares >= TRADE_UNIT:
                    cost = max_shares * buy_price
                    fee = cost * self._commission
                    position = max_shares
                    entry_price = buy_price
                    entry_date = d
                    cash -= (cost + fee)

            # 止损检查
            if position > 0 and entry_price > 0 and signal and signal.stop_loss > 0:
                loss_pct = (close / entry_price - 1) * 100
                if loss_pct <= -signal.stop_loss:
                    sell_value = position * close * (1 - self._slippage)
                    fee = sell_value * self._commission
                    stamp = sell_value * self._stamp_tax
                    revenue = sell_value - fee - stamp
                    pnl = revenue - position * entry_price

                    transactions.append(TradeRecord(
                        entry_date=entry_date,
                        exit_date=d,
                        entry_price=entry_price,
                        exit_price=close,
                        shares=position,
                        direction="long",
                        pnl=round(pnl, 2),
                        return_pct=round((close / entry_price - 1) * 100, 2),
                        exit_reason="stop_loss",
                    ))

                    cash += revenue
                    position = 0
                    entry_price = 0.0
                    entry_date = None

        # 收盘：强制平仓
        if position > 0:
            last_row = data.iloc[-1]
            close_price = float(last_row["Close"])
            sell_value = position * close_price * (1 - self._slippage)
            fee = sell_value * self._commission
            stamp = sell_value * self._stamp_tax
            revenue = sell_value - fee - stamp
            pnl = revenue - position * entry_price

            transactions.append(TradeRecord(
                entry_date=entry_date or date.min,
                exit_date=last_row["date"].date(),
                entry_price=entry_price,
                exit_price=close_price,
                shares=position,
                direction="long",
                pnl=round(pnl, 2),
                return_pct=round((close_price / entry_price - 1) * 100, 2),
                exit_reason="end_of_period",
            ))

            cash += revenue
            position = 0

        # 最终净值
        final_equity = cash
        daily_equity[data.iloc[-1]["date"].date().isoformat()] = round(final_equity, 2)

        self._position = 0
        self._trades = transactions
        self._daily_equity = daily_equity
        self._daily_nav = self._equity_to_nav(daily_equity)

    def _run_hold_strategy(self, data: pd.DataFrame) -> None:
        """买入持有基线策略"""
        if len(data) < MIN_HOLD_DAYS:
            return

        first_close = float(data.iloc[0]["Close"])
        last_close = float(data.iloc[-1]["Close"])
        shares = int(self._capital / first_close / TRADE_UNIT) * TRADE_UNIT
        cost = shares * first_close
        fee = cost * self._commission
        cash = self._capital - cost - fee

        # 最后一天卖出
        sell_value = shares * last_close * (1 - self._slippage)
        sell_fee = sell_value * self._commission
        stamp = sell_value * self._stamp_tax
        revenue = sell_value - sell_fee - stamp
        final_cash = cash + revenue

        # 每日净值
        daily_equity: dict[str, float] = {}
        for _, row in data.iterrows():
            val = cash + shares * float(row["Close"])
            daily_equity[row["date"].date().isoformat()] = round(val, 2)

        self._trades.append(TradeRecord(
            entry_date=data.iloc[0]["date"].date(),
            exit_date=data.iloc[-1]["date"].date(),
            entry_price=first_close,
            exit_price=last_close,
            shares=shares,
            direction="long",
            pnl=round(final_cash - self._capital, 2),
            return_pct=round((final_cash / self._capital - 1) * 100, 2),
            exit_reason="hold",
        ))
        self._daily_equity = daily_equity
        self._daily_nav = self._equity_to_nav(daily_equity)

    def _equity_to_nav(self, daily_equity: dict) -> dict:
        """将权益曲线转为净值序列（基准=1.0）"""
        if not daily_equity:
            return {}
        sorted_dates = sorted(daily_equity.keys())
        base = daily_equity[sorted_dates[0]]
        if base == 0:
            return {}
        return {d: round(daily_equity[d] / base, 4) for d in sorted_dates}

    def _calculate_result(self) -> BacktestResult:  # noqa: PLR0912
        """从交易记录计算绩效指标"""
        total_trades = len(self._trades)
        total_return_pct = 0.0
        annual_return = 0.0
        max_dd = 0.0
        win_rate = 0.0
        profit_loss_ratio = 0.0
        sharpe = 0.0
        calmar = 0.0

        if total_trades == 0:
            return BacktestResult(
                initial_capital=self._capital,
                final_capital=self._capital,
                total_trades=0,
                params_used=self._get_params(),
                daily_equity=self._daily_equity,
            )

        # 胜率和盈亏比
        winning_trades = [t for t in self._trades if t.pnl > 0]
        losing_trades = [t for t in self._trades if t.pnl <= 0]
        win_rate = len(winning_trades) / total_trades if total_trades else 0.0

        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        avg_loss = abs(np.mean([t.pnl for t in losing_trades])) if losing_trades else 1.0
        profit_loss_ratio = avg_win / avg_loss if avg_loss != 0 else 0.0

        # 总收益率
        if self._daily_nav:
            sorted_dates = sorted(self._daily_nav.keys())
            start_nav = self._daily_nav[sorted_dates[0]]
            end_nav = self._daily_nav[sorted_dates[-1]]
            total_return_pct = (end_nav / start_nav - 1) if start_nav > 0 else 0.0
        else:
            total_return_pct = 0.0

        total_return_pct *= 100  # 转百分比

        # 年化收益率
        if self._start and self._end:
            days = (self._end - self._start).days
            if days > 0 and total_return_pct > ANNUAL_PCT:
                annual_return = ((1 + total_return_pct / 100) ** (365.0 / days) - 1) * 100

        # 最大回撤
        if self._daily_equity:
            sorted_vals = [
                self._daily_equity[k]
                for k in sorted(self._daily_equity.keys())
            ]
            if sorted_vals:
                peak = sorted_vals[0]
                for val in sorted_vals:
                    peak = max(peak, val)
                    dd = (peak - val) / peak if peak > 0 else 0
                    max_dd = max(max_dd, dd)

        # 夏普比率
        if self._daily_nav:
            sorted_dates = sorted(self._daily_nav.keys())
            daily_returns_pct = []
            for i in range(1, len(sorted_dates)):
                prev = self._daily_nav[sorted_dates[i - 1]]
                curr = self._daily_nav[sorted_dates[i]]
                if prev > 0:
                    daily_returns_pct.append((curr - prev) / prev)

            if len(daily_returns_pct) > 1:
                mean_ret = np.mean(daily_returns_pct)
                std_ret = np.std(daily_returns_pct, ddof=1)
                sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0.0

        # Calmar比率
        calmar = annual_return / (max_dd * 100) if max_dd > 0 else 0.0

        return BacktestResult(
            strategy_type="",
            start_date=self._start,
            end_date=self._end,
            initial_capital=self._capital,
            final_capital=round(
                self._daily_equity.get(
                    sorted(self._daily_equity.keys())[-1],
                    self._capital,
                )
                if self._daily_equity
                else self._capital,
                2,
            ),
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_dd, 4),
            win_rate=round(win_rate, 4),
            profit_loss_ratio=round(profit_loss_ratio, 4),
            total_trades=total_trades,
            total_return_pct=round(total_return_pct, 2),
            sharpe_ratio=round(sharpe, 4),
            calmar_ratio=round(calmar, 4),
            params_used=self._get_params(),
            daily_equity=self._daily_equity,
        )

    def _get_params(self) -> dict:
        return {
            "commission": self._commission,
            "slippage": self._slippage,
            "capital": self._capital,
        }

    def _empty_result(self, reason: str) -> BacktestResult:
        logger.warning("回测未执行: %s", reason)
        return BacktestResult(
            initial_capital=self._capital,
            final_capital=self._capital,
            total_trades=0,
            params_used=self._get_params(),
            daily_equity={},
        )


# ═══════════════════════════════════════════════════════════════════
# PortfolioBacktester — 组合回测器
# ═══════════════════════════════════════════════════════════════════


class PortfolioBacktester:
    """组合回测器"""

    def __init__(
        self,
        strategy_type: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
        initial_capital: float = 1_000_000.0,
        params: dict | None = None,
    ):
        self.strategy_type = strategy_type
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.params = params or {}

    def run_multi(
        self,
        klines_dict: dict[str, pd.DataFrame],
        signals_dict: dict[str, list[TradeSignal]],
    ) -> PortfolioResult:
        results: dict[str, BacktestResult] = {}

        for stock_code, klines in klines_dict.items():
            if stock_code not in signals_dict:
                continue

            engine = BacktestingEngine()
            engine.set_parameters(
                data=klines,
                start=self.start_date,
                end=self.end_date,
                capital=self.initial_capital / max(len(klines_dict), 1),
                commission=COMMISSION_RATE,
                signals=signals_dict[stock_code],
            )
            result = engine.run()
            result.strategy_type = self.strategy_type
            results[stock_code] = result

        return self._aggregate(results)

    def _aggregate(self, results: dict[str, BacktestResult]) -> PortfolioResult:
        if not results:
            return PortfolioResult(
                strategy_type=self.strategy_type,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_trades=0,
            )

        # 合并每日净值
        all_dates: set[str] = set()
        for r in results.values():
            all_dates.update(r.daily_equity.keys())

        combined_equity: dict[str, float] = {}
        for d in sorted(all_dates):
            total = sum(r.daily_equity.get(d, 0.0) for r in results.values())
            combined_equity[d] = round(total, 2)

        # 聚合统计
        total_trades = sum(r.total_trades for r in results.values())
        sorted_equity_dates = sorted(combined_equity.keys())
        if combined_equity and sorted_equity_dates:
            final_capital = combined_equity.get(sorted_equity_dates[-1], self.initial_capital)
        else:
            final_capital = self.initial_capital

        # 胜率（加权平均按交易数）
        weighted_win = sum(r.win_rate * r.total_trades for r in results.values())
        weighted_win = weighted_win / total_trades if total_trades > 0 else 0.0

        # 最大回撤
        max_dd = 0.0
        if combined_equity:
            sorted_vals = [combined_equity[k] for k in sorted(combined_equity.keys())]
            peak = sorted_vals[0]
            for val in sorted_vals:
                peak = max(peak, val)
                dd = (peak - val) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)

        # 年化
        annual_return = 0.0
        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days
            total_ret = (final_capital / self.initial_capital - 1)  # noqa: PLR2004
            total_ret = total_ret if self.initial_capital > 0 else 0
            if days > 0 and total_ret > -1:
                annual_return = ((1 + total_ret) ** (365.0 / days) - 1) * 100

        return PortfolioResult(
            strategy_type=self.strategy_type,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_dd, 4),
            win_rate=round(weighted_win, 4),
            total_trades=total_trades,
            stock_count=len(results),
            daily_equity=combined_equity,
            individual_results=results,
        )
