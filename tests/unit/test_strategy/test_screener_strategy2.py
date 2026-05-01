"""测试策略二「趋势动量低吸」粗筛

条件：
1. 板块资金集中度 ≥ 12%（连续2日）
2. MA5 > MA10 > MA20 > MA60（多头排列）
3. ADX ≥ 25
4. 近3日成交量 < 5日均量80%，跌幅 < 3%
5. 非ST、非次新股
6. 日均成交额 ≥ 3亿
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.strategy.screener import (
    calculate_adx,
    is_bullish_arrangement,
    is_volume_shrinking,
    screen_strategy2,
)


class TestIsBullishArrangement:
    """均线多头排列检测"""

    def test_bullish_arrangement(self):
        """给定：MA5 > MA10 > MA20 > MA60
        返回：True"""
        mas = {"ma5": 15.0, "ma10": 14.0, "ma20": 13.0, "ma60": 12.0}
        assert is_bullish_arrangement(mas)

    def test_not_bullish_ma5_lower(self):
        """给定：MA5 < MA10
        返回：False"""
        mas = {"ma5": 13.0, "ma10": 14.0, "ma20": 13.0, "ma60": 12.0}
        assert not is_bullish_arrangement(mas)

    def test_missing_key(self):
        """给定：缺少某均线
        返回：False"""
        mas = {"ma5": 15.0, "ma10": 14.0}
        assert not is_bullish_arrangement(mas)

    def test_equal_values_accepted(self):
        """给定：MA5 == MA10 > MA20
        返回：True（等于也接受）"""
        mas = {"ma5": 14.0, "ma10": 14.0, "ma20": 13.0, "ma60": 12.0}
        assert is_bullish_arrangement(mas)


class TestCalculateADX:
    """ADX（平均趋向指数）计算"""

    def test_adx_returns_positive(self):
        """给定：有趋势的K线数据
        返回：ADX ≥ 0"""
        np.random.seed(42)
        klines = pd.DataFrame({
            "high": np.cumsum(np.random.randn(30)) + 100,
            "low": np.cumsum(np.random.randn(30)) + 98,
            "close": np.cumsum(np.random.randn(30)) + 99,
        })
        adx = calculate_adx(klines, period=14)
        assert adx >= 0
        assert adx <= 100

    def test_adx_strong_trend(self):
        """给定：强烈上升趋势
        返回：较高ADX值"""
        klines = pd.DataFrame({
            "high": [100 + i * 2 for i in range(30)],
            "low": [99 + i * 2 for i in range(30)],
            "close": [99.5 + i * 2 for i in range(30)],
        })
        adx = calculate_adx(klines, period=14)
        assert adx > 20  # 强趋势

    def test_adx_insufficient_data(self):
        """给定：数据不足
        返回：0"""
        klines = pd.DataFrame({
            "high": [100, 101],
            "low": [99, 100],
            "close": [99.5, 100.5],
        })
        adx = calculate_adx(klines, period=14)
        assert adx == 0.0

    def test_adx_no_data(self):
        """给定：空数据
        返回：0"""
        assert calculate_adx(pd.DataFrame(), period=14) == 0.0


class TestIsVolumeShrinking:
    """缩量回调检测"""

    def test_volume_shrinking(self):
        """给定：近3日量 < 5日均量80%
        返回：True"""
        klines = pd.DataFrame({
            "volume": [1_000_000] * 5 + [600_000, 550_000, 500_000],
        })
        assert is_volume_shrinking(klines, lookback=3, ma_window=5, ratio=0.8)

    def test_volume_not_shrinking(self):
        """给定：近3日量 ≈ 5日均量
        返回：False"""
        klines = pd.DataFrame({
            "volume": [1_000_000] * 5 + [950_000, 980_000, 960_000],
        })
        assert not is_volume_shrinking(klines, lookback=3, ma_window=5, ratio=0.8)

    def test_insufficient_data(self):
        """给定：数据不足
        返回：False"""
        klines = pd.DataFrame({"volume": [100, 200]})
        assert not is_volume_shrinking(klines, lookback=3, ma_window=5, ratio=0.8)

    def test_no_volume_column(self):
        """给定：无volume列
        返回：False"""
        assert not is_volume_shrinking(pd.DataFrame({"close": [10]}), lookback=3, ma_window=5, ratio=0.8)


class TestScreenStrategy2:
    """策略二完整粗筛"""

    @patch("src.strategy.screener.get_db_connection")
    def test_finds_candidates(self, mock_get_db):
        """给定：模拟DB中符合策略二条件的股票
        返回：非空候选列表"""
        # stocks
        stocks_data = [("000001.SZ", "平安银行", date(2023, 1, 1), None)]

        # 模拟上升趋势K线 — 从8元涨到16元
        klines_raw = []
        for i in range(70):
            close = 8.0 + (i / 70.0) * 8.0
            hi = close * 1.02; lo = close * 0.98
            klines_raw.append((hi, lo, close, 1_500_000_000, 1_500_000_000, 0.5))

        # 最近3天缩量 + 微回调
        for j in range(3):
            old = klines_raw[-(j+1)]
            klines_raw[-(j+1)] = (old[0], old[1], old[2], 300_000_000, 300_000_000, -0.2)

        # SQL 返回 DESC 顺序（最新在前）
        klines = list(reversed(klines_raw))

        # sector_data — 板块资金集中度 ≥ 12%（只返回SQL查的3个字段）
        sector_data = [
            ("商业航天", 15.0, date.today()),
            ("商业航天", 13.5, date.today() - timedelta(days=1)),
        ]

        fi = [0]
        def fetchall_se():
            i = fi[0]
            fi[0] += 1
            if i == 0: return sector_data      # 第一次: 板块集中度
            elif i == 1: return stocks_data    # 第二次: 所有股票
            else: return klines                # 后续: 每只股票的K线

        c = MagicMock()
        cur = MagicMock()
        cur.fetchall.side_effect = fetchall_se
        c.cursor.return_value = cur
        mock_get_db.return_value = c

        candidates = screen_strategy2()
        assert len(candidates) > 0

    @patch("src.strategy.screener.get_db_connection")
    def test_requires_sector_concentration(self, mock_get_db):
        """给定：板块资金集中度不足
        排除"""
        stocks_data = [("000001.SZ", "平安银行", date(2023, 1, 1), None)]
        klines = [(date(2026, 5, 1), 11.0, 9.0, 10.0, 1_000_000, 1_000_000, 0.5)] * 66
        sector_data = [("商业航天", 5.0, date.today())]

        fi = [0]
        def fetchall_se():
            i = fi[0]; fi[0] += 1
            if i == 0: return stocks_data
            elif i == 1: return klines
            else: return sector_data

        c = MagicMock()
        cur = MagicMock()
        cur.fetchall.side_effect = fetchall_se
        c.cursor.return_value = cur
        mock_get_db.return_value = c

        candidates = screen_strategy2()
        assert len(candidates) == 0
