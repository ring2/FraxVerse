"""测试 AKShare 个股资金流向采集器

P0-2.3: 个股资金流向 + 大单/小单分布
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.fund_flow_collector import (
    clean_fund_flow,
    fetch_individual_fund_flow,
    save_fund_flow_to_db,
)


class TestFetchIndividualFundFlow:
    """个股资金流向获取"""

    @patch("src.data.fund_flow_collector.ak.stock_individual_fund_flow")
    def test_returns_fund_flow_dataframe(self, mock_flow):
        """给定：正常股票代码
        返回：非空 DataFrame，含必要字段（清洗后）"""
        mock_flow.return_value = pd.DataFrame({
            "日期": ["2026-01-02", "2026-01-03"],
            "股票代码": ["000001", "000001"],
            "最新价": [10.5, 10.8],
            "涨跌幅": [2.5, -0.5],
            "主力净流入-净额": [15000000.0, -8000000.0],
            "主力净流入-净占比": [8.5, -4.2],
            "超大单净流入-净额": [9000000.0, -5000000.0],
            "超大单净流入-净占比": [5.1, -2.6],
            "大单净流入-净额": [6000000.0, -3000000.0],
            "大单净流入-净占比": [3.4, -1.6],
            "中单净流入-净额": [-7000000.0, 4000000.0],
            "中单净流入-净占比": [-4.0, 2.1],
            "小单净流入-净额": [-8000000.0, 4000000.0],
            "小单净流入-净占比": [-4.5, 2.1],
        })
        raw = fetch_individual_fund_flow("000001")
        assert not raw.empty
        df = clean_fund_flow(raw)
        required = {"trade_date", "main_net_amount", "main_net_pct"}
        assert required.issubset(set(df.columns))

    @patch("src.data.fund_flow_collector.ak.stock_individual_fund_flow")
    def test_market_code_suffix(self, mock_flow):
        """给定：带市场后缀（000001.SZ）
        传参：自动截断为 000001"""
        fetch_individual_fund_flow("000001.SZ")
        mock_flow.assert_called_once()
        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs.get("stock") == "000001"

    @patch("src.data.fund_flow_collector.ak.stock_individual_fund_flow")
    def test_network_error_returns_empty(self, mock_flow):
        """给定：网络异常
        返回：空 DataFrame"""
        mock_flow.side_effect = ConnectionError("timeout")
        df = fetch_individual_fund_flow("000001")
        assert df.empty

    @patch("src.data.fund_flow_collector.ak.stock_individual_fund_flow")
    def test_empty_response(self, mock_flow):
        """给定：无数据
        返回：空 DataFrame"""
        mock_flow.return_value = pd.DataFrame()
        df = fetch_individual_fund_flow("000001")
        assert df.empty


class TestCleanFundFlow:
    """资金流向数据清洗"""

    def test_renames_columns(self):
        """给定：原始列名
        清洗后：英文列名"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02"],
            "股票代码": ["000001"],
            "主力净流入-净额": [15000000.0],
            "主力净流入-净占比": [8.5],
            "超大单净流入-净额": [9000000.0],
            "超大单净流入-净占比": [5.1],
            "大单净流入-净额": [6000000.0],
            "中小单净流入-净额": [-8000000.0],
        })
        cleaned = clean_fund_flow(raw)
        assert "main_net_amount" in cleaned.columns
        assert "trade_date" in cleaned.columns

    def test_empty_input(self):
        """给定：空 DataFrame
        返回：空"""
        assert clean_fund_flow(pd.DataFrame()).empty

    def test_large_order_pct_derived(self):
        """给定：有超大单和大单数据
        清洗后：large_order_pct = 超大单占比 + 大单占比"""
        raw = pd.DataFrame({
            "日期": ["2026-01-02"],
            "超大单净流入-净占比": [5.1],
            "大单净流入-净占比": [3.4],
        })
        cleaned = clean_fund_flow(raw)
        assert cleaned["large_order_pct"].iloc[0] == pytest.approx(8.5)


class TestSaveFundFlow:
    """资金流向入库"""

    @patch("src.data.fund_flow_collector.get_db_connection")
    def test_save_inserts_data(self, mock_get_db):
        """给定：清洗后的 DataFrame
        入库：写入 fund_flows 表"""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn

        df = pd.DataFrame({
            "trade_date": [date(2026, 1, 2)],
            "main_net_amount": [15000000.0],
            "large_order_pct": [8.5],
            "small_order_pct": [-4.5],
        })
        save_fund_flow_to_db(df, "000001.SZ")
        assert mock_conn.cursor.return_value.execute.called
        assert mock_conn.commit.called

    @patch("src.data.fund_flow_collector.get_db_connection")
    def test_save_empty(self, mock_get_db):
        """给定：空 DataFrame
        入库：不操作"""
        save_fund_flow_to_db(pd.DataFrame(), "000001.SZ")
        mock_get_db.assert_not_called()
