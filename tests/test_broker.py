"""
TDD: 执行层（Broker）测试
"""

from investment_agent.core.types import Direction, Order, Signal
from investment_agent.execution.broker import MockBroker


class TestMockBroker:
    def test_send_and_fill_market_order(self):
        broker = MockBroker(commission_rate=0.0003, slippage=0.001)
        broker.set_price_source(lambda s: 100.0)

        sig = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=None)
        order = Order(signal=sig)
        broker.send_order(order)

        fills = broker.get_fills()
        assert len(fills) == 1
        fill = fills[0]
        assert fill.symbol == "A"
        assert fill.quantity == 100
        # 买入滑点：成交价 >= 100
        assert fill.price >= 100.0
        assert fill.commission > 0

    def test_sell_slippage(self):
        broker = MockBroker(slippage=0.001)
        broker.set_price_source(lambda s: 100.0)

        sig = Signal(symbol="A", direction=Direction.SELL, quantity=50, price=None)
        order = Order(signal=sig)
        broker.send_order(order)

        fills = broker.get_fills()
        assert fills[0].price <= 100.0  # 卖出滑点更便宜

    def test_cancel_order(self):
        broker = MockBroker(fill_probability=0.0)  # 永远不成交
        broker.set_price_source(lambda s: 100.0)

        sig = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=None)
        order = Order(signal=sig)
        broker.send_order(order)

        assert broker.cancel_order(order.order_id) is True
        assert order.status.value == "cancelled"
