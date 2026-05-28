"""
TDD: 数据层测试
"""

import pandas as pd

from investment_agent.data.mock_provider import MockDataProvider


class TestMockDataProvider:
    def test_get_daily_bars_structure(self):
        dp = MockDataProvider()
        df = dp.get_daily_bars("000001.SZ", limit=50)
        assert not df.empty
        assert set(df.columns) >= {"open", "high", "low", "close", "volume"}
        assert len(df) == 50

    def test_get_current_price(self):
        dp = MockDataProvider()
        price = dp.get_current_price("000001.SZ")
        assert price is not None
        assert price > 0

    def test_reproducibility(self):
        dp1 = MockDataProvider(seed=123)
        dp2 = MockDataProvider(seed=123)
        df1 = dp1.get_daily_bars("A", limit=30)
        df2 = dp2.get_daily_bars("A", limit=30)
        pd.testing.assert_frame_equal(df1, df2)

    def test_get_symbols(self):
        dp = MockDataProvider()
        syms = dp.get_symbols()
        assert isinstance(syms, list)
        assert len(syms) >= 4
