"""Mock 数据提供器 —— 用于回测与单元测试
生成带趋势的随机游走价格序列
"""

from datetime import datetime

import numpy as np
import pandas as pd

from .provider import DataProvider


class MockDataProvider(DataProvider):
    """模拟数据提供器，支持趋势和均值回归两种模式"""

    def __init__(
        self,
        seed: int = 42,
        trend: float = 0.0,  # 每日漂移
        volatility: float = 0.02,  # 日波动率
        initial_price: float = 100.0,
    ):
        self.seed = seed
        self.trend = trend
        self.volatility = volatility
        self.initial_price = initial_price
        self._data_cache: dict[str, pd.DataFrame] = {}
        self._rng = np.random.default_rng(seed)

    def _generate(self, symbol: str, periods: int) -> pd.DataFrame:
        if symbol in self._data_cache:
            return self._data_cache[symbol]

        rng = np.random.default_rng(self.seed + hash(symbol) % 10000)
        returns = rng.normal(self.trend, self.volatility, periods)
        prices = self.initial_price * np.exp(np.cumsum(returns))

        # 使用固定锚点日期，保证所有symbol时间轴一致
        anchor = datetime(2024, 1, 1)
        dates = pd.date_range(start=anchor, periods=periods, freq="B")
        df = pd.DataFrame(index=dates)
        df["close"] = prices
        df["open"] = df["close"] * (1 + rng.normal(0, 0.005, periods))
        df["high"] = df[["open", "close"]].max(axis=1) * (1 + np.abs(rng.normal(0, 0.01, periods)))
        df["low"] = df[["open", "close"]].min(axis=1) * (1 - np.abs(rng.normal(0, 0.01, periods)))
        df["volume"] = rng.integers(1_000_000, 10_000_000, periods)

        self._data_cache[symbol] = df
        return df

    def get_daily_bars(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        df = self._generate(symbol, limit)
        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]
        return df.copy()

    def get_current_price(self, symbol: str) -> float | None:
        df = self._generate(symbol, 100)
        return float(df["close"].iloc[-1])

    def get_symbols(self, market: str = "A") -> list[str]:
        return ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH"]
