"""Quick backtest demo using the InvestmentAgent."""

from investment_agent import InvestmentAgent
from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.strategy.momentum import DualMAStrategy
from investment_agent.strategy.mean_reversion import MeanReversionStrategy
from investment_agent.execution.risk import RiskManager


def main() -> None:
    """Run a simple backtest with two strategies."""
    agent = InvestmentAgent(
        data_provider=MockDataProvider(seed=42, trend=0.0003, volatility=0.02),
        strategies=[
            DualMAStrategy(fast=5, slow=20),
            MeanReversionStrategy(),
        ],
        risk_manager=RiskManager(
            config={
                "max_single_position": 0.5,
                "max_total_exposure": 0.95,
                "stop_loss_pct": -0.10,
            }
        ),
        initial_cash=1_000_000,
    )

    print("=== Stock Analysis ===")
    print(agent.analyze("000001.SZ"))

    print("\n=== Backtest Results ===")
    metrics = agent.backtest(symbols=["000001.SZ", "600000.SH"], days=120)
    print(metrics)


if __name__ == "__main__":
    main()
