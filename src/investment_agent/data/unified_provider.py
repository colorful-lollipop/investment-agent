"""统一多市场数据提供器 —— A股/港股/美股.

数据源:
- A股: 腾讯实时接口 (qt.gtimg.cn) + yfinance 历史数据
- 港股: yfinance
- 美股: yfinance

不依赖 AKShare（网络不稳定），不依赖付费 API.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd
import requests


class UnifiedDataProvider:
    """统一多市场数据提供器."""

    # 市场映射
    MARKET_A = "A"
    MARKET_HK = "HK"
    MARKET_US = "US"

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._session = requests.Session()

    def _detect_market(self, symbol: str) -> str:
        """检测标的市场."""
        if symbol.endswith(".SZ") or symbol.endswith(".SH") or symbol.endswith(".BJ"):
            return self.MARKET_A
        if symbol.endswith(".HK"):
            return self.MARKET_HK
        return self.MARKET_US

    def _normalize_symbol(self, symbol: str) -> str:
        """转换为各数据源需要的格式."""
        market = self._detect_market(symbol)
        if market == self.MARKET_A:
            # sz300750 -> sz300750, sh600519 -> sh600519
            code = symbol.lower().split(".")[1] + symbol.lower().split(".")[0]
            return code
        if market == self.MARKET_HK:
            # 0700.HK -> 0700.hk
            return symbol.lower()
        # US: AAPL -> AAPL
        return symbol.upper()

    def get_current_price(self, symbol: str) -> float | None:
        """获取最新价格."""
        market = self._detect_market(symbol)
        if market == self.MARKET_A:
            return self._get_a_price(symbol)
        return self._get_yf_price(symbol)

    def _get_a_price(self, symbol: str) -> float | None:
        """通过腾讯接口获取 A 股实时价格."""
        code = self._normalize_symbol(symbol)
        url = f"https://qt.gtimg.cn/q={code}"
        try:
            resp = self._session.get(url, timeout=10)
            text = resp.text
            # 解析: v_sz300750="51~宁德时代~300750~415.68~..."
            match = re.search(r'v_[^"]+="([^"]+)"', text)
            if not match:
                return None
            parts = match.group(1).split("~")
            if len(parts) > 3:
                return float(parts[3])
        except Exception:
            pass
        return None

    def _get_yf_price(self, symbol: str) -> float | None:
        """通过 yfinance 获取港/美股最新价格."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", interval="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return None

    def get_daily_bars(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """获取日线数据."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            period = "2y" if limit > 400 else "1y"
            df = ticker.history(period=period, interval="1d")
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df = df.rename(
                columns={
                    "Date": "date",
                    "Datetime": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            df = df.set_index("date")
            if start:
                df = df[df.index >= start]
            if end:
                df = df[df.index <= end]
            return df
        except Exception:
            return pd.DataFrame()

    def get_intraday_bars(
        self,
        symbol: str,
        interval: str = "1h",
        period: str = "5d",
    ) -> pd.DataFrame:
        """获取分钟/小时级别数据.

        Args:
            symbol: 标的代码
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 1h
            period: 1d, 5d, 1mo
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df = df.rename(
                columns={
                    "Datetime": "datetime",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )
            df["datetime"] = pd.to_datetime(df["datetime"]).dt.tz_localize(None)
            df = df.set_index("datetime")
            return df
        except Exception:
            return pd.DataFrame()

    def get_batch_prices(self, symbols: list[str]) -> dict[str, float]:
        """批量获取价格."""
        results: dict[str, float] = {}
        a_symbols = [s for s in symbols if self._detect_market(s) == self.MARKET_A]
        other_symbols = [s for s in symbols if s not in a_symbols]

        # A 股批量查询
        if a_symbols:
            codes = ",".join(self._normalize_symbol(s) for s in a_symbols)
            url = f"https://qt.gtimg.cn/q={codes}"
            try:
                resp = self._session.get(url, timeout=10)
                for line in resp.text.strip().split(";"):
                    match = re.search(r'v_([^=]+)="([^"]+)"', line)
                    if not match:
                        continue
                    code_key = match.group(1)  # sz300750
                    parts = match.group(2).split("~")
                    if len(parts) > 3:
                        # 还原为原始 symbol 格式
                        original = next(
                            (s for s in a_symbols if self._normalize_symbol(s) == code_key),
                            None,
                        )
                        if original:
                            results[original] = float(parts[3])
            except Exception:
                pass

        # 港/美股逐个查询
        for sym in other_symbols:
            price = self.get_current_price(sym)
            if price:
                results[sym] = price

        return results
