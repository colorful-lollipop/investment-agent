"""示例：机器学习融合预测策略
使用 XGBoost-LSTM 融合模型预测未来5日收益，TopK选股
"""

import pandas as pd

from investment_agent.core.types import Context, Direction, Signal
from investment_agent.ml.predictor import XGBLSTMFusionPredictor
from investment_agent.strategy.base import BaseStrategy


class MLFusionStrategy(BaseStrategy):
    """ML融合策略
    1. 对每个标的训练/更新预测模型
    2. 预测未来收益，选择TopK买入
    3. NDrop调仓：每天只卖出最差的1只，买入1只新标的
    """

    def __init__(
        self, topk: int = 5, ndrop: int = 1, capital_pct: float = 0.1, name: str = "MLFusion"
    ):
        super().__init__(
            name=name,
            params={
                "topk": topk,
                "ndrop": ndrop,
                "capital_pct": capital_pct,
            },
        )
        self.topk = topk
        self.ndrop = ndrop
        self.capital_pct = capital_pct
        self._models: dict[str, XGBLSTMFusionPredictor] = {}
        self._scores: dict[str, float] = {}

    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        symbol = data.attrs.get("symbol", "UNKNOWN")
        if len(data) < 60:
            return []

        # 训练/更新模型
        if symbol not in self._models:
            self._models[symbol] = XGBLSTMFusionPredictor(seq_len=10)
        model = self._models[symbol]
        try:
            model.fit(data)
            score = model.predict(data)
        except Exception:
            score = 0.0
        self._scores[symbol] = score

        # 此策略只输出分数，实际调仓在 portfolio 层面做
        # 为简化，这里返回基于分数的信号（如果分数显著为正且未持仓则买入）
        signals = []
        pos = context.account.get_position(symbol)

        if score > 0.02 and pos.quantity == 0:  # 预期收益>2%
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.BUY,
                    quantity=self._compute_qty(data["close"].iloc[-1], context),
                    price=None,
                    confidence=min(0.95, 0.5 + score * 10),
                    reason=f"ML预测5日收益{score:.2%}",
                    strategy=self.name,
                )
            )
        elif score < -0.01 and pos.quantity > 0:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.SELL,
                    quantity=pos.quantity,
                    price=None,
                    confidence=min(0.95, 0.5 - score * 10),
                    reason=f"ML预测5日收益{score:.2%}，止盈止损",
                    strategy=self.name,
                )
            )

        return signals

    def _compute_qty(self, price: float, context: Context) -> float:
        cash_to_use = context.account.total_value * self.capital_pct
        return max(1, int(cash_to_use / price / 100)) * 100
