"""数据提供层抽象 —— 屏蔽不同数据源的差异
参考 vnpy / qlib 设计：统一 Bar / Tick 接口
"""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class DataProvider(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_daily_bars(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """获取日K线数据
        返回 DataFrame，列至少包含: open, high, low, close, volume
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float | None:
        """获取最新价格"""
        pass

    @abstractmethod
    def get_symbols(self, market: str = "A") -> list[str]:
        """获取标的列表"""
        pass

    def warmup(self, symbols: list[str], days: int = 60) -> dict[str, pd.DataFrame]:
        """批量预热历史数据，用于策略初始化"""
        result = {}
        for sym in symbols:
            df = self.get_daily_bars(sym, limit=days)
            if df is not None and not df.empty:
                result[sym] = df
        return result
