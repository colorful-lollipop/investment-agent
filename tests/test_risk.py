"""
TDD: 风控层测试 —— 金融大牛第一原则
"""

import pytest

from investment_agent.core.types import Account, Direction, Position, Signal
from investment_agent.execution.risk import RiskManager


class TestRiskManager:
    @pytest.fixture
    def rm(self):
        return RiskManager(
            config={
                "stop_loss_pct": -0.07,
                "max_single_position": 0.20,
                "max_total_exposure": 0.90,
                "blacklist": ["ST0001"],
                "order_cooldown_seconds": 60,
            }
        )

    @pytest.fixture
    def account(self):
        acc = Account(cash=1_000_000)
        return acc

    def test_blacklist_blocks(self, rm, account):
        sig = Signal(symbol="ST0001", direction=Direction.BUY, quantity=100, price=10.0)
        order = rm.evaluate(sig, account, {"ST0001": 10.0})
        assert order is None

    def test_position_limit_blocks(self, rm, account):
        # 让账户已经持有大量该标的
        account.positions["A"] = Position(
            symbol="A", quantity=100_000, avg_cost=10.0, last_price=20.0
        )
        account.positions["A"].update_market_price(20.0)
        sig = Signal(symbol="A", direction=Direction.BUY, quantity=10_000, price=20.0)
        order = rm.evaluate(sig, account, {"A": 20.0})
        assert order is None

    def test_stop_loss_blocks(self, rm, account):
        account.positions["A"] = Position(
            symbol="A", quantity=1000, avg_cost=100.0, last_price=90.0
        )
        account.positions["A"].update_market_price(90.0)
        sig = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=90.0)
        order = rm.evaluate(sig, account, {"A": 90.0})
        assert order is None

    def test_valid_signal_passes(self, rm, account):
        sig = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=10.0)
        order = rm.evaluate(sig, account, {"A": 10.0})
        assert order is not None
        assert order.signal == sig

    def test_duplicate_protection(self, rm, account):
        sig = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=10.0)
        order1 = rm.evaluate(sig, account, {"A": 10.0})
        assert order1 is not None
        order2 = rm.evaluate(sig, account, {"A": 10.0})
        assert order2 is None  # 冷却期内重复下单被拦截
