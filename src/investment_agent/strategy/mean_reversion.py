"""均值回归策略：布林带 + RSI 多因子协同确认
参考金融大牛经验：超卖+触及下轨 → 做多；超买+触及上轨 → 做空/平仓
"""

import pandas as pd

from investment_agent.core.types import Context, Direction, Signal
from investment_agent.strategy.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略
    买入：RSI < 30 且 价格 <= 布林带下轨（超卖反弹）
    卖出：RSI > 70 且 价格 >= 布林带上轨（超买回落）
    """

    def __init__(
        self,
        bb_window: int = 20,
        bb_std: float = 2.0,
        rsi_window: int = 14,
        rsi_buy: float = 30.0,
        rsi_sell: float = 70.0,
        name: str = "MeanReversion",
        capital_pct: float = 0.1,
    ):
        super().__init__(
            name=name,
            params={
                "bb_window": bb_window,
                "bb_std": bb_std,
                "rsi_window": rsi_window,
                "rsi_buy": rsi_buy,
                "rsi_sell": rsi_sell,
                "capital_pct": capital_pct,
            },
        )
        self.bb_window = bb_window
        self.bb_std = bb_std
        self.rsi_window = rsi_window
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell

    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        if len(data) < self.bb_window + 5:
            return []

        symbol = data.attrs.get("symbol", "UNKNOWN")
        close = data["close"]
        current_price = close.iloc[-1]

        # 布林带
        ma = close.rolling(self.bb_window).mean()
        std = close.rolling(self.bb_window).std()
        upper = (ma + self.bb_std * std).iloc[-1]
        lower = (ma - self.bb_std * std).iloc[-1]

        # RSI
        rsi = self._compute_rsi(close).iloc[-1]

        signals = []
        pos = context.account.get_position(symbol)

        # 买入条件：超卖 + 触及下轨
        if rsi < self.rsi_buy and current_price <= lower:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.BUY,
                    quantity=self._compute_quantity(current_price, context),
                    price=None,
                    confidence=min(0.9, (self.rsi_buy - rsi) / self.rsi_buy + 0.3),
                    reason=f"RSI={rsi:.1f}超卖,价格触及布林带下轨({lower:.2f})",
                    strategy=self.name,
                )
            )

        # 卖出条件：超买 + 触及上轨（且有持仓）
        elif rsi > self.rsi_sell and current_price >= upper and pos.quantity > 0:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.SELL,
                    quantity=pos.quantity,
                    price=None,
                    confidence=min(0.9, (rsi - self.rsi_sell) / (100 - self.rsi_sell) + 0.3),
                    reason=f"RSI={rsi:.1f}超买,价格触及布林带上轨({upper:.2f})",
                    strategy=self.name,
                )
            )

        return signals

    def _compute_rsi(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / self.rsi_window, min_periods=self.rsi_window).mean()
        avg_loss = loss.ewm(alpha=1 / self.rsi_window, min_periods=self.rsi_window).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _compute_quantity(self, price: float, context: Context) -> float:
        capital_pct = self.params.get("capital_pct", 0.1)
        cash_to_use = context.account.total_value * capital_pct
        return max(1, int(cash_to_use / price / 100)) * 100
