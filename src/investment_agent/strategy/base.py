"""策略基类 —— 参考 Backtrader / vnpy 设计
所有策略必须继承此类，实现 generate_signals
"""

from abc import ABC, abstractmethod

import pandas as pd

from investment_agent.core.types import Context, Fill, Signal


class BaseStrategy(ABC):
    """策略抽象基类"""

    def __init__(self, name: str = "", params: dict | None = None):
        self.name = name or self.__class__.__name__
        self.params = params or {}
        self._initialized = False

    def initialize(self, context: Context) -> None:
        """策略初始化钩子，可预热指标等"""
        self._initialized = True

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        """基于行情数据生成交易信号
        :param data: 当前标的的 DataFrame（含历史）
        :param context: 运行时上下文（账户、时间等）
        :return: Signal 列表（可能为空）
        """
        pass

    def on_fill(self, fill: Fill, context: Context) -> None:  # noqa: B027
        """成交回调 —— 用于策略状态更新（如记录持仓成本、调整网格等）."""
        pass

    def on_market_open(self, context: Context) -> None:  # noqa: B027
        """开盘事件钩子."""
        pass

    def on_market_close(self, context: Context) -> None:  # noqa: B027
        """收盘事件钩子."""
        pass
