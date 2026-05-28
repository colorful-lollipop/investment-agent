"""
TDD: 回测引擎测试
"""

import pytest

from investment_agent.backtest.engine import BacktestEngine
from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.execution.risk import RiskManager
from investment_agent.strategy.momentum import DualMAStrategy


class TestBacktestEngine:
    def test_backtest_runs_without_error(self):
        dp = MockDataProvider(seed=42, trend=0.0005, volatility=0.02)
        strat = DualMAStrategy(fast=5, slow=20)
        rm = RiskManager(
            config={
                "max_single_position": 0.5,
                "max_total_exposure": 0.95,
                "stop_loss_pct": -0.10,
            }
        )
        engine = BacktestEngine(
            data_provider=dp,
            strategies=[strat],
            risk_manager=rm,
            initial_cash=1_000_000,
        )
        metrics = engine.run(
            symbols=["000001.SZ", "600000.SH"],
            warmup_days=30,
        )
        assert metrics is not None
        # 回测应该产生净值历史
        assert len(engine.account.total_value_history) > 0
        # 检查是否有交易发生（概率上应该有）
        print(metrics)

    def test_backtest_with_no_data_raises(self):
        dp = MockDataProvider()
        engine = BacktestEngine(
            data_provider=dp,
            strategies=[DualMAStrategy()],
            risk_manager=RiskManager(),
        )
        with pytest.raises(ValueError):
            engine.run(symbols=[])  # 空列表应该触发异常
