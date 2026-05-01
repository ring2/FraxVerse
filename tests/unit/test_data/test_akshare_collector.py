"""测试 AKShare 数据采集器

TDD 原则：
  1. 每个测试用例定义明确的行为契约
  2. 实现前跑测试 → 预期全红（未通过）
  3. 实现后跑测试 → 预期全绿（通过）
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.collector import (
    CollectorError,
    clean_kline,
    fetch_daily_kline,
    save_kline_to_db,
)


class TestFetchDailyKline:
    """P0-2.1 AKShare 日K线采集 — 基础采集"""

    @patch("src.data.collector.ak.stock_zh_a_hist")
    def test_fetch_returns_nonempty_dataframe(self, mock_akshare):
        """给定：一只正常股票代码
        返回：非空DataFrame（原始AKShare格式）"""
        mock_df = pd.DataFrame({
            "日期": ["2026-01-02", "2026-01-03"],
            "开盘": [10.0, 10.5],
            "最高": [11.0, 11.2],
            "最低": [9.8, 10.3],
            "收盘": [10.8, 10.9],
            "成交量": [1_000_000, 1_200_000],
            "成交额": [10_800_000, 13_080_000],
            "振幅": [3.5, 2.8],
            "涨跌幅": [2.5, 0.93],
            "涨跌额": [0.25, 0.10],
            "换手率": [1.5, 1.8],
        })
        mock_akshare.return_value = mock_df

        # fetch 返回原始数据，不做清洗
        df = fetch_daily_kline("000001.SZ")
        assert not df.empty
        # 然后清洗
        cleaned = clean_kline(df)
        required = ["open", "high", "low", "close", "volume"]
        assert all(col in cleaned.columns for col in required)

    @patch("src.data.collector.ak.stock_zh_a_hist")
    def test_fetch_respects_date_range(self, mock_akshare):
        """给定：日期范围参数
        传入：正确的参数给akshare"""
        fetch_daily_kline("000001.SZ", start="2026-01-01", end="2026-01-31")
        mock_akshare.assert_called_once()
        call_kwargs = mock_akshare.call_args.kwargs
        assert call_kwargs["start_date"] == "20260101"
        assert call_kwargs["end_date"] == "20260131"

    @patch("src.data.collector.ak.stock_zh_a_hist")
    def test_fetch_invalid_code_returns_empty(self, mock_akshare):
        """给定：无效股票代码
        返回：空DataFrame，不抛异常"""
        mock_akshare.return_value = pd.DataFrame()
        df = fetch_daily_kline("INVALID")
        assert df.empty

    @patch("src.data.collector.ak.stock_zh_a_hist")
    def test_fetch_akshare_network_error(self, mock_akshare):
        """给定：AKShare 网络异常
        返回：CollectorError，不崩溃"""
        mock_akshare.side_effect = ConnectionError("Network timeout")
        with pytest.raises(CollectorError, match="采集失败.*000001"):
            fetch_daily_kline("000001.SZ")


class TestCleanKline:
    """P0-2.1 AKShare 日K线采集 — 数据清洗"""

    def test_clean_renames_columns(self):
        """给定：原始AKShare列名（中文）
        清洗后：映射为英文列名"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02"],
            "开盘": [10.0],
            "最高": [11.0],
            "最低": [9.8],
            "收盘": [10.8],
            "成交量": [1_000_000],
            "成交额": [10_800_000],
            "振幅": [3.5],
            "涨跌幅": [2.5],
            "涨跌额": [0.25],
            "换手率": [1.5],
        })
        cleaned = clean_kline(raw)
        expected_cols = {
            "trade_date", "open", "high", "low", "close",
            "volume", "amount", "amplitude", "pct_change", "change", "turnover",
        }
        assert expected_cols.issubset(set(cleaned.columns))

    def test_clean_deduplicates_dates(self):
        """给定：有重复日期的数据
        清洗后：无重复日期行"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02", "2026-01-02"],
            "开盘": [10.0, 10.0],
            "最高": [11.0, 11.0],
            "最低": [9.8, 9.8],
            "收盘": [10.8, 10.8],
            "成交量": [1_000_000, 1_000_000],
        })
        cleaned = clean_kline(raw)
        assert len(cleaned) == 1

    def test_clean_parses_dates(self):
        """给定：字符串日期
        清洗后：trade_date 为 datetime.date 类型"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02"],
            "开盘": [10.0],
            "最高": [11.0],
            "最低": [9.8],
            "收盘": [10.8],
            "成交量": [1_000_000],
        })
        cleaned = clean_kline(raw)
        assert isinstance(cleaned["trade_date"].iloc[0], (date, pd.Timestamp))

    def test_clean_empty_input(self):
        """给定：空DataFrame
        返回：空DataFrame，不报错"""
        raw = pd.DataFrame()
        cleaned = clean_kline(raw)
        assert cleaned.empty

    def test_clean_missing_columns_preserves_partial_data(self):
        """给定：缺失部分字段的DataFrame
        清洗后：可用字段保留，缺失字段含默认值"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02"],
            "收盘": [10.8],
            "成交量": [1_000_000],
        })
        cleaned = clean_kline(raw)
        assert not cleaned.empty
        assert "close" in cleaned.columns
        assert cleaned["close"].iloc[0] == 10.8


class TestSaveKlineToDb:
    """P0-2.1 AKShare 日K线采集 — 入库"""

    @patch("src.data.collector.get_db_connection")
    def test_save_inserts_data(self, mock_get_db):
        """给定：清洗后的DataFrame
        入库：数据被写入daily_klines表"""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn

        df = pd.DataFrame({
            "trade_date": [date(2026, 1, 2)],
            "open": [10.0],
            "high": [11.0],
            "low": [9.8],
            "close": [10.8],
            "volume": [1_000_000],
            "amount": [1_080_0000.0],
        })

        save_kline_to_db(df, "000001.SZ")
        assert mock_conn.cursor.return_value.execute.called
        assert mock_conn.commit.called

    @patch("src.data.collector.get_db_connection")
    def test_save_empty_dataframe(self, mock_get_db):
        """给定：空DataFrame
        入库：不执行任何SQL，不报错"""
        df = pd.DataFrame()
        save_kline_to_db(df, "000001.SZ")
        mock_get_db.assert_not_called()
