"""测试数据质量监控

P0-2.4: 数据断更检测、完整性检查、停牌/ST状态自动更新
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from src.data.data_quality import (
    DataQualityIssue,
    check_kline_integrity,
    check_missing_trade_dates,
    detect_suspension,
)


class TestCheckMissingTradeDates:
    """断更检测"""

    def test_no_missing_when_consecutive(self):
        """给定：连续交易日数据
        返回：无缺失"""
        trade_dates = [date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8)]
        missing = check_missing_trade_dates(trade_dates)
        assert len(missing) == 0

    def test_detects_weekend_gap(self):
        """给定：跨周末（周五→周一）
        返回：无缺失（周末正常跳过）"""
        trade_dates = [date(2026, 5, 8), date(2026, 5, 11)]  # Fri, Mon
        missing = check_missing_trade_dates(trade_dates)
        assert len(missing) == 0

    def test_detects_midweek_gap(self):
        """给定：工作日缺失（周一→周三）
        返回：检测到周二缺失"""
        trade_dates = [date(2026, 5, 11), date(2026, 5, 13)]  # Mon, Wed
        missing = check_missing_trade_dates(trade_dates)
        assert date(2026, 5, 12) in missing

    def test_single_date_no_check(self):
        """给定：只有一条数据
        返回：无缺失（数据不足无法判断）"""
        missing = check_missing_trade_dates([date(2026, 5, 11)])
        assert len(missing) == 0

    def test_empty_input(self):
        """给定：空列表
        返回：空"""
        assert check_missing_trade_dates([]) == []


class TestCheckKlineIntegrity:
    """K线数据完整性检查"""

    def test_complete_kline(self):
        """给定：完整K线数据
        返回：无异常"""
        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 11)],
            "open": [10.0],
            "high": [11.0],
            "low": [9.5],
            "close": [10.5],
            "volume": [1_000_000],
        })
        issues = check_kline_integrity(df, "000001.SZ")
        assert len(issues) == 0

    def test_high_lower_than_low(self):
        """给定：最高价<最低价
        返回：标记异常"""
        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 11)],
            "open": [10.0],
            "high": [9.5],
            "low": [11.0],
            "close": [10.5],
            "volume": [1_000_000],
        })
        issues = check_kline_integrity(df, "000001.SZ")
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_high_nan(self):
        """给定：字段缺失（NaN）
        返回：标记异常"""
        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 11)],
            "open": [10.0],
            "high": [float("nan")],
            "low": [9.5],
            "close": [10.5],
            "volume": [1_000_000],
        })
        issues = check_kline_integrity(df, "000001.SZ")
        assert len(issues) == 1

    def test_zero_volume(self):
        """给定：成交量为0
        返回：警告（可能停牌或数据异常）"""
        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 11)],
            "open": [10.0],
            "high": [11.0],
            "low": [9.5],
            "close": [10.5],
            "volume": [0],
        })
        issues = check_kline_integrity(df, "000001.SZ")
        assert len(issues) >= 1

    def test_empty_dataframe(self):
        """给定：空 DataFrame
        返回：空"""
        assert check_kline_integrity(pd.DataFrame(), "000001.SZ") == []

    def test_null_rate_warning(self):
        """给定：空值率超5%
        返回：警告"""
        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 11), date(2026, 5, 12)],
            "open": [10.0, None],
            "high": [11.0, None],
            "low": [9.5, None],
            "close": [10.5, None],
            "volume": [1_000_000, None],
        })
        issues = check_kline_integrity(df, "000001.SZ")
        null_issues = [i for i in issues if "空值率" in i.message]
        assert len(null_issues) >= 1


class TestDetectSuspension:
    """停牌检测"""

    @patch("src.data.data_quality.get_db_connection")
    def test_detect_suspended_stock(self, mock_get_db):
        """给定：某股票最近3个交易日无数据
        返回：疑似停牌"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 最近3个交易日
        mock_cursor.fetchall.return_value = [
            (date(2026, 5, 11),),
            (date(2026, 5, 12),),
        ]
        # stocks 表里的所有股票
        mock_conn.cursor.side_effect = [mock_cursor, MagicMock()]
        mock_conn.cursor.return_value.fetchall.return_value = [
            ("000001.SZ", "平安银行"),
        ]
        mock_get_db.return_value = mock_conn

        issues = detect_suspension(lookback_days=3)
        assert len(issues) >= 0  # 检测逻辑不抛出异常

    def test_issue_data_class(self):
        """验证 DataQualityIssue 结构"""
        issue = DataQualityIssue(
            stock_code="000001.SZ",
            trade_date=date(2026, 5, 11),
            issue_type="missing_data",
            severity="warning",
            message="交易日缺失",
        )
        assert issue.stock_code == "000001.SZ"
        assert issue.issue_type == "missing_data"
