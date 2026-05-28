"""
TDD: 核心领域模型单元测试
"""

from datetime import datetime

import pytest

from investment_agent.core.types import (
    Account,
    Direction,
    Fill,
    Order,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    Signal,
)


class TestSignal:
    def test_signal_creation(self):
        s = Signal(
            symbol="000001.SZ",
            direction=Direction.BUY,
            quantity=100,
            price=10.5,
            confidence=0.85,
            reason="MA金叉",
            strategy="DualMA",
        )
        assert s.symbol == "000001.SZ"
        assert s.direction == Direction.BUY
        assert s.confidence == 0.85
        assert s.reason == "MA金叉"

    def test_signal_confidence_validation(self):
        with pytest.raises(ValueError):
            Signal(symbol="A", direction=Direction.BUY, quantity=1, price=None, confidence=1.5)

    def test_signal_quantity_validation(self):
        with pytest.raises(ValueError):
            Signal(symbol="A", direction=Direction.BUY, quantity=0, price=None, confidence=0.5)


class TestOrder:
    def test_order_from_signal(self):
        sig = Signal(symbol="000001.SZ", direction=Direction.SELL, quantity=50, price=None)
        order = Order(signal=sig, order_type=OrderType.MARKET)
        assert order.symbol == "000001.SZ"
        assert order.direction == Direction.SELL
        assert order.remaining_quantity == 50.0
        assert order.status == OrderStatus.PENDING


class TestFill:
    def test_fill_updates_account_buy(self):
        acc = Account(cash=100_000)
        fill = Fill(
            order_id="o1",
            symbol="000001.SZ",
            direction=Direction.BUY,
            quantity=100,
            price=10.0,
            commission=5.0,
        )
        acc.apply_fill(fill)
        assert acc.cash == 100_000 - (100 * 10.0 + 5.0)
        pos = acc.get_position("000001.SZ")
        assert pos.quantity == 100
        assert pos.avg_cost == 10.0

    def test_fill_updates_account_sell(self):
        acc = Account(cash=100_000)
        # 先买入
        acc.apply_fill(Fill("o1", "A", Direction.BUY, 100, 10.0, 0))
        # 再卖出
        acc.apply_fill(Fill("o2", "A", Direction.SELL, 50, 12.0, 5.0))
        assert acc.cash == 100_000 - 1000 + (50 * 12.0 - 5.0)
        pos = acc.get_position("A")
        assert pos.quantity == 50


class TestPosition:
    def test_position_pnl(self):
        pos = Position(symbol="A", quantity=100, avg_cost=10.0)
        pos.update_market_price(12.0)
        assert pos.market_value == 1200.0
        assert pos.unrealized_pnl == 200.0
        assert pos.return_pct == 0.2


class TestAccount:
    def test_total_value(self):
        acc = Account(cash=50_000)
        acc.positions["A"] = Position(symbol="A", quantity=100, avg_cost=10.0, last_price=15.0)
        acc.positions["A"].update_market_price(15.0)
        assert acc.total_value == 50_000 + 1500

    def test_snapshot_history(self):
        acc = Account(cash=100_000)
        acc.record_snapshot(datetime(2024, 1, 1))
        assert len(acc.total_value_history) == 1


class TestPortfolio:
    def test_max_drawdown(self):
        acc = Account()
        acc.total_value_history = [
            (datetime(2024, 1, 1), 100),
            (datetime(2024, 1, 2), 110),
            (datetime(2024, 1, 3), 90),
            (datetime(2024, 1, 4), 105),
        ]
        port = Portfolio(account=acc)
        # peak=110, trough=90 => dd = 20/110 ≈ 0.1818
        assert port.max_drawdown == pytest.approx(20 / 110, rel=1e-4)

    def test_weight(self):
        acc = Account(cash=50_000)
        acc.positions["A"] = Position(symbol="A", quantity=100, last_price=10.0)
        acc.positions["A"].update_market_price(10.0)
        port = Portfolio(account=acc)
        assert port.weight("A") == pytest.approx(1000 / 51000, rel=1e-4)
