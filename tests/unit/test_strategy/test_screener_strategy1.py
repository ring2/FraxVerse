"""测试策略一「周期底部量能异动」粗筛

P0-3.1: 近60日跌幅≥20%、5日内有单日大跌、市值50-500亿、非ST非次新、流动性≥1亿
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from src.strategy.screener import (
    StrategyCandidate,
    has_drop_in_window,
    has_sufficient_liquidity,
    is_new_stock,
    is_st_stock,
    screen_strategy1,
)


class TestIsStStock:
    """ST/警示股票排除"""

    def test_detects_st_prefix(self):
        assert is_st_stock("*ST平安")
        assert is_st_stock("ST康美")
        assert is_st_stock("SST前锋")

    def test_detects_st_in_name(self):
        assert is_st_stock("ST百花")
        assert is_st_stock("*ST博信")

    def test_normal_stock_not_st(self):
        assert not is_st_stock("贵州茅台")
        assert not is_st_stock("平安银行")
        assert not is_st_stock("东方财富")

    def test_edge_case_empty(self):
        assert is_st_stock("")
        assert is_st_stock(None)


class TestIsNewStock:
    """次新股排除（上市≥180天）"""

    def test_old_enough(self):
        today = date(2026, 5, 12)
        listing = today - timedelta(days=200)  # 200天前上市
        assert not is_new_stock(listing, today)

    def test_too_new(self):
        today = date(2026, 5, 12)
        listing = today - timedelta(days=100)  # 100天前
        assert is_new_stock(listing, today)

    def test_exactly_180_days(self):
        today = date(2026, 5, 12)
        listing = today - timedelta(days=180)
        assert not is_new_stock(listing, today)

    def test_no_listing_date(self):
        assert is_new_stock(None, date(2026, 5, 12))


class TestHasDropInWindow:
    """近N日内存在单日大跌检测"""

    def test_has_drop(self):
        klines = pd.DataFrame({
            "pct_change": [-1.5, -6.2, 2.0, -5.5, 0.5],
        })
        assert has_drop_in_window(klines, window=5, threshold=-5.0)

    def test_no_drop(self):
        klines = pd.DataFrame({
            "pct_change": [-1.5, -3.0, 2.0, -4.5, 0.5],
        })
        assert not has_drop_in_window(klines, window=5, threshold=-5.0)

    def test_empty(self):
        assert not has_drop_in_window(pd.DataFrame(), window=5, threshold=-5.0)

    def test_no_pct_column(self):
        df = pd.DataFrame({"close": [10, 11]})
        assert not has_drop_in_window(df, window=5, threshold=-5.0)


class TestHasSufficientLiquidity:
    """流动性检查（日均成交额≥1亿）"""

    def test_sufficient(self):
        klines = pd.DataFrame({
            "amount": [2_000_000_000, 1_500_000_000, 3_000_000_000],
        })
        assert has_sufficient_liquidity(klines, min_daily_amount=1_000_000_000)

    def test_insufficient(self):
        klines = pd.DataFrame({
            "amount": [50_000_000, 30_000_000, 80_000_000],
        })
        assert not has_sufficient_liquidity(klines, min_daily_amount=1_000_000_000)

    def test_empty(self):
        assert not has_sufficient_liquidity(pd.DataFrame(), min_daily_amount=1_000_000_000)

    def test_no_amount_column(self):
        assert not has_sufficient_liquidity(pd.DataFrame({"close": [10]}), min_daily_amount=1_000_000_000)


class TestScreenStrategy1:
    """策略一完整粗筛"""

    @patch("src.strategy.screener.get_db_connection")
    def test_screen_finds_candidates(self, mock_get_db):
        """给定：模拟数据库中有符合条件的数据
        返回：候选列表（非空）"""
        stocks_data = [("000001.SZ", "平安银行", date(2024, 1, 1), None)]

        klines_data = []
        for i in range(60):
            td = date(2026, 3, 1) + timedelta(days=i)
            if td.weekday() >= 5:
                continue
            close = 20.0 - (59 - i) * 0.17
            pct = -0.5
            klines_data.append((td, close, close * 1.01, close * 0.99, close, 1_000_000, 2_000_000_000, pct))
        for j in range(5):
            klines_data[-(j + 1)] = klines_data[-(j + 1)][:7] + (-6.0,)

        fetchall_results = [stocks_data, klines_data]
        fetch_index = [0]

        def fetchall_side_effect():
            i = fetch_index[0]
            fetch_index[0] += 1
            return fetchall_results[i]

        c = MagicMock()
        cur = MagicMock()
        cur.fetchall.side_effect = fetchall_side_effect
        c.cursor.return_value = cur
        mock_get_db.return_value = c

        candidates = screen_strategy1()
        assert len(candidates) > 0

    @patch("src.strategy.screener.get_db_connection")
    def test_screen_excludes_st(self, mock_get_db):
        """给定：ST股票
        排除"""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("000001.SZ", "ST平安", date(2024, 1, 1), None),
        ]
        mock_conn.cursor.return_value = mock_cursor

        candidates = screen_strategy1()
        st_codes = [c.stock_code for c in candidates if "ST" in c.stock_name or "ST" in str(c.stock_code)]
        assert len(st_codes) == 0

    def test_candidate_dataclass(self):
        """验证 StrategyCandidate 结构"""
        c = StrategyCandidate(
            stock_code="000001.SZ",
            stock_name="平安银行",
            score=85.0,
            drop_pct=22.5,
            daily_amount=2_000_000_000,
            reason="底部放量异动",
        )
        assert c.stock_code == "000001.SZ"
        assert c.score == 85.0
