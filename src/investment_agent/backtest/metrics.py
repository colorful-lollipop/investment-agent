"""回测绩效指标 —— 参考 pyfolio / empyrical 设计
年化收益、夏普、最大回撤、Calmar、胜率、盈亏比
"""

from datetime import datetime

import numpy as np
import pandas as pd


class PerformanceMetrics:
    """绩效分析器"""

    def __init__(self, value_history: list[tuple[datetime, float]], risk_free_rate: float = 0.03):
        self.value_history = value_history
        self.risk_free_rate = risk_free_rate
        self._df = self._build_series()

    def _build_series(self) -> pd.Series:
        if not self.value_history:
            return pd.Series(dtype=float)
        df = pd.DataFrame(self.value_history, columns=["timestamp", "value"])
        df = df.set_index("timestamp").sort_index()
        return df["value"]

    @property
    def total_return(self) -> float:
        if len(self._df) < 2:
            return 0.0
        return float(self._df.iloc[-1] / self._df.iloc[0]) - 1.0

    @property
    def annual_return(self) -> float:
        tr = self.total_return
        days = (self._df.index[-1] - self._df.index[0]).days
        if days <= 0:
            return 0.0
        years = days / 365.0
        return float((1 + tr) ** (1 / years)) - 1.0

    @property
    def max_drawdown(self) -> float:
        if self._df.empty:
            return 0.0
        peak = self._df.cummax()
        dd = (peak - self._df) / peak
        return float(dd.max())

    @property
    def sharpe_ratio(self) -> float:
        returns = self._df.pct_change().dropna()
        if returns.empty or returns.std() == 0:
            return 0.0
        excess = returns.mean() * 252 - self.risk_free_rate
        volatility = returns.std() * np.sqrt(252)
        return float(excess / volatility)

    @property
    def calmar_ratio(self) -> float:
        mdd = self.max_drawdown
        if mdd == 0:
            return 0.0
        return self.annual_return / mdd

    @property
    def volatility_annual(self) -> float:
        returns = self._df.pct_change().dropna()
        return float(returns.std() * np.sqrt(252))

    def report(self) -> dict:
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "volatility_annual": self.volatility_annual,
        }

    def __repr__(self) -> str:
        r = self.report()
        lines = ["Performance Report:", "-" * 30]
        for k, v in r.items():
            if isinstance(v, float):
                lines.append(f"  {k:20s}: {v:>10.4f}")
            else:
                lines.append(f"  {k:20s}: {v}")
        return "\n".join(lines)
