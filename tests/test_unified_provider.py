"""UnifiedDataProvider 测试."""

from investment_agent.data.unified_provider import UnifiedDataProvider


class TestUnifiedDataProvider:
    def test_detect_market(self) -> None:
        p = UnifiedDataProvider()
        assert p._detect_market("300750.SZ") == "A"
        assert p._detect_market("600519.SH") == "A"
        assert p._detect_market("0700.HK") == "HK"
        assert p._detect_market("AAPL") == "US"

    def test_normalize_a_share(self) -> None:
        p = UnifiedDataProvider()
        assert p._normalize_symbol("300750.SZ") == "sz300750"
        assert p._normalize_symbol("600519.SH") == "sh600519"

    def test_get_a_price(self) -> None:
        p = UnifiedDataProvider()
        price = p._get_a_price("300750.SZ")
        assert price is not None
        assert price > 0

    def test_get_yf_price(self) -> None:
        p = UnifiedDataProvider()
        price = p._get_yf_price("AAPL")
        assert price is not None
        assert price > 0

    def test_batch_prices(self) -> None:
        p = UnifiedDataProvider()
        prices = p.get_batch_prices(["300750.SZ", "AAPL"])
        assert "300750.SZ" in prices or "AAPL" in prices
        for v in prices.values():
            assert v > 0

    def test_daily_bars(self) -> None:
        p = UnifiedDataProvider()
        df = p.get_daily_bars("AAPL", limit=10)
        assert not df.empty
        assert "close" in df.columns

    def test_intraday_bars(self) -> None:
        p = UnifiedDataProvider()
        df = p.get_intraday_bars("AAPL", interval="1h", period="2d")
        assert not df.empty
        assert "close" in df.columns
