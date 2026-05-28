"""
TDD: Agent 主控集成测试
"""

import os

import pytest

from investment_agent.agent import InvestmentAgent
from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.execution.risk import RiskManager
from investment_agent.strategy.mean_reversion import MeanReversionStrategy
from investment_agent.strategy.momentum import DualMAStrategy


class TestInvestmentAgent:
    @pytest.fixture
    def agent(self):
        dp = MockDataProvider(seed=42)
        return InvestmentAgent(
            data_provider=dp,
            strategies=[
                DualMAStrategy(fast=5, slow=20),
                MeanReversionStrategy(),
            ],
            risk_manager=RiskManager(
                config={
                    "max_single_position": 0.5,
                    "max_total_exposure": 0.95,
                }
            ),
            initial_cash=1_000_000,
        )

    def test_analyze_returns_dict(self, agent):
        result = agent.analyze("000001.SZ")
        assert "symbol" in result
        assert "trend" in result
        assert result["data_points"] >= 20

    def test_backtest_runs(self, agent):
        metrics = agent.backtest(
            symbols=["000001.SZ", "600000.SH"],
            days=120,
        )
        assert metrics is not None
        assert metrics.total_return is not None

    def test_run_daily(self, agent):
        result = agent.run_daily(["000001.SZ", "600000.SH"])
        assert "total_value" in result
        assert result["total_value"] > 0

    def test_from_config(self):
        # 确保配置文件存在
        assert os.path.exists("config/config.yaml")
        agent = InvestmentAgent.from_config("config/config.yaml")
        assert len(agent.strategies) >= 1
        assert agent.account.cash > 0
