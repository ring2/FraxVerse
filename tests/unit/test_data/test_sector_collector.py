"""测试 AKShare 板块数据采集器

P0-2.2: 板块成分股 + 板块资金流向
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from src.data.sector_collector import (
    fetch_sector_constituents,
    fetch_sector_fund_flow,
    fetch_sector_list,
    save_sector_data_to_db,
    save_sector_fund_flow_to_db,
)


class TestFetchSectorList:
    """板块列表获取"""

    @patch("src.data.sector_collector.ak.stock_board_industry_name_em")
    def test_returns_sector_list(self, mock_list):
        """给定：调用板块列表接口
        返回：非空 DataFrame，含行业代码和名称"""
        mock_list.return_value = pd.DataFrame({
            "板块名称": ["商业航天", "人工智能", "半导体"],
            "板块代码": ["BK0965", "BK0800", "BK0688"],
        })
        df = fetch_sector_list()
        assert not df.empty
        assert "sector_name" in df.columns
        assert len(df) == 3

    @patch("src.data.sector_collector.ak.stock_board_industry_name_em")
    def test_network_error_returns_empty(self, mock_list):
        """给定：网络异常
        返回：空 DataFrame，不抛异常"""
        mock_list.side_effect = ConnectionError("timeout")
        df = fetch_sector_list()
        assert df.empty


class TestFetchSectorConstituents:
    """板块成分股获取"""

    @patch("src.data.sector_collector.ak.stock_board_industry_cons_em")
    def test_returns_constituents(self, mock_cons):
        """给定：板块名称
        返回：成分股列表"""
        mock_cons.return_value = pd.DataFrame({
            "代码": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "名称": ["平安银行", "万科A", "中兴通讯"],
        })
        df = fetch_sector_constituents("商业航天")
        assert not df.empty
        assert "stock_code" in df.columns
        assert len(df) == 3

    @patch("src.data.sector_collector.ak.stock_board_industry_cons_em")
    def test_invalid_sector_returns_empty(self, mock_cons):
        """给定：无效板块名称
        返回：空 DataFrame"""
        mock_cons.return_value = pd.DataFrame()
        df = fetch_sector_constituents("不存在的板块")
        assert df.empty

    @patch("src.data.sector_collector.ak.stock_board_industry_cons_em")
    def test_network_error_returns_empty(self, mock_cons):
        """给定：网络异常
        返回：空 DataFrame"""
        mock_cons.side_effect = ConnectionError("timeout")
        df = fetch_sector_constituents("商业航天")
        assert df.empty


class TestFetchSectorFundFlow:
    """板块资金流向获取"""

    @patch("src.data.sector_collector.ak.stock_fund_flow_industry")
    def test_returns_fund_flow(self, mock_flow):
        """给定：板块名称
        返回：资金流 DataFrame"""
        mock_flow.return_value = pd.DataFrame({
            "日期": ["2026-05-01"],
            "行业名称": ["商业航天"],
            "主力净流入-净额": [12_500_000.0],
            "主力净流入-净占比": [12.5],
            "超大单净流入-净额": [8_200_000.0],
            "超大单净流入-净占比": [8.2],
            "大单净流入-净额": [4_300_000.0],
            "大单净流入-净占比": [4.3],
            "中单净流入-净额": [-5_100_000.0],
            "中单净流入-净占比": [-5.1],
            "小单净流入-净额": [-6_400_000.0],
            "小单净流入-净占比": [-6.4],
        })
        df = fetch_sector_fund_flow("商业航天")
        assert not df.empty
        assert "trade_date" in df.columns
        assert "main_net_amount" in df.columns

    @patch("src.data.sector_collector.ak.stock_fund_flow_industry")
    def test_empty_response(self, mock_flow):
        """给定：无数据
        返回：空 DataFrame"""
        mock_flow.return_value = pd.DataFrame()
        df = fetch_sector_fund_flow("商业航天")
        assert df.empty


class TestSaveSectorData:
    """板块数据入库"""

    @patch("src.data.sector_collector.get_db_connection")
    def test_save_sector_data_inserts(self, mock_get_db):
        """给定：板块数据
        入库：写入 sector_data 表"""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn

        df = pd.DataFrame({
            "sector_code": ["BK0965"],
            "sector_name": ["商业航天"],
            "sector_type": ["industry"],
            "capital_ratio": [12.5],
            "leader_stocks": [["000001.SZ", "000002.SZ"]],
        })

        save_sector_data_to_db(df, trade_date=date(2026, 5, 1))
        assert mock_conn.cursor.return_value.execute.called
        assert mock_conn.commit.called

    @patch("src.data.sector_collector.get_db_connection")
    def test_save_sector_empty(self, mock_get_db):
        """给定：空 DataFrame
        入库：不操作"""
        save_sector_data_to_db(pd.DataFrame(), trade_date=date(2026, 5, 1))
        mock_get_db.assert_not_called()

    @patch("src.data.sector_collector.get_db_connection")
    def test_save_fund_flow_inserts(self, mock_get_db):
        """给定：资金流数据
        入库：写入 sector_data（更新 capital_ratio 等字段）"""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn

        df = pd.DataFrame({
            "trade_date": [date(2026, 5, 1)],
            "sector_name": ["商业航天"],
            "main_net_amount": [12_500_000.0],
            "main_net_pct": [12.5],
            "turnover_rate": [3.2],
            "change_pct": [2.5],
        })

        save_sector_fund_flow_to_db(df)
        assert mock_conn.cursor.return_value.execute.called
        assert mock_conn.commit.called
