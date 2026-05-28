"""Investment Agent — A modular quantitative investment analysis framework.

Supports backtesting, strategy development, risk management,
and machine-learning-powered prediction.

Example:
    >>> from investment_agent import InvestmentAgent
    >>> agent = InvestmentAgent.from_config("config/config.yaml")
    >>> metrics = agent.backtest(symbols=["000001.SZ"], days=180)
"""

from investment_agent.__version__ import __version__
from investment_agent.agent import InvestmentAgent

__all__ = ["__version__", "InvestmentAgent"]
