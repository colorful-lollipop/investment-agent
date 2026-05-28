"""动量策略：双均线交叉（Dual Moving Average Crossover）
经典趋势跟踪策略，参考海龟交易与均线突破思想
"""

import pandas as pd

from investment_agent.core.types import Context, Direction, Signal
from investment_agent.strategy.base import BaseStrategy


class DualMAStrategy(BaseStrategy):
    """双均线交叉策略
    短期均线上穿长期均线 → 买入（金叉）
    短期均线下穿长期均线 → 卖出（死叉）
    """

    def __init__(
        self, fast: int = 5, slow: int = 20, name: str = "DualMA", capital_pct: float = 0.1
    ):
        super().__init__(name=name, params={"fast": fast, "slow": slow, "capital_pct": capital_pct})
        self.fast = fast
        self.slow = slow
        self._last_state: dict[str, int] = {}  # symbol -> 1=多头, -1=空头, 0=空仓

    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        if len(data) < self.slow + 5:
            return []

        symbol = data.attrs.get("symbol", "UNKNOWN")
        close = data["close"]
        ma_fast = close.rolling(self.fast).mean().iloc[-1]
        ma_slow = close.rolling(self.slow).mean().iloc[-1]
        prev_fast = close.rolling(self.fast).mean().iloc[-2]
        prev_slow = close.rolling(self.slow).mean().iloc[-2]

        current_price = close.iloc[-1]
        signals = []

        # 金叉检测：前一日 fast < slow，今日 fast > slow
        if prev_fast <= prev_slow and ma_fast > ma_slow:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.BUY,
                    quantity=self._compute_quantity(current_price, context),
                    price=None,
                    confidence=0.7,
                    reason=f"MA{self.fast} 上穿 MA{self.slow} 金叉",
                    strategy=self.name,
                )
            )

        # 死叉检测
        elif prev_fast >= prev_slow and ma_fast < ma_slow:
            pos = context.account.get_position(symbol)
            if pos.quantity > 0:
                signals.append(
                    Signal(
                        symbol=symbol,
                        direction=Direction.SELL,
                        quantity=pos.quantity,  # 清仓
                        price=None,
                        confidence=0.7,
                        reason=f"MA{self.fast} 下穿 MA{self.slow} 死叉",
                        strategy=self.name,
                    )
                )

        return signals

    def _compute_quantity(self, price: float, context: Context) -> float:
        """简单仓位计算：用总资金的10%买入"""
        capital_pct = self.params.get("capital_pct", 0.1)
        cash_to_use = context.account.total_value * capital_pct
        return max(1, int(cash_to_use / price / 100)) * 100  # A股100股一手
