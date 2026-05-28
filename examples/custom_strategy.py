"""Example of a custom strategy implementation."""

import pandas as pd

from investment_agent.core.types import Context, Direction, Signal
from investment_agent.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):
    """Simple buy-and-hold strategy for demonstration."""

    def __init__(self, name: str = "BuyAndHold") -> None:
        super().__init__(name=name)
        self._bought: set[str] = set()

    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        """Buy on the first bar and hold forever."""
        symbol = data.attrs.get("symbol", "UNKNOWN")
        if symbol in self._bought or len(data) < 2:
            return []

        self._bought.add(symbol)
        price = data["close"].iloc[-1]
        quantity = max(1, int(context.account.cash * 0.1 / price / 100)) * 100

        return [
            Signal(
                symbol=symbol,
                direction=Direction.BUY,
                quantity=quantity,
                price=None,
                confidence=1.0,
                reason="First bar buy-and-hold",
                strategy=self.name,
            )
        ]
