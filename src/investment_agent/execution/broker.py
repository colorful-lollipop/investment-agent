"""交易执行层 —— 参考 vnpy 的网关设计
Broker 负责订单路由、状态管理和成交回报
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

from investment_agent.core.types import Direction, Fill, Order, OrderStatus


class Broker(ABC):
    """券商/交易所接口抽象"""

    @abstractmethod
    def send_order(self, order: Order) -> bool:
        """提交订单"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass

    @abstractmethod
    def get_fills(self) -> list[Fill]:
        """获取最新成交回报"""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> float:
        """查询持仓"""
        pass


class MockBroker(Broker):
    """模拟券商 —— 用于回测与单元测试
    支持：滑点、佣金、成交量约束、部分成交
    """

    def __init__(
        self,
        commission_rate: float = 0.0003,  # 万分之三
        min_commission: float = 5.0,  # 最低佣金
        slippage: float = 0.001,  # 0.1% 滑点
        fill_probability: float = 1.0,  # 成交概率
    ):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage = slippage
        self.fill_probability = fill_probability
        self._fills: list[Fill] = []
        self._pending_orders: list[Order] = []
        self._price_source: Callable | None = None  # 注入价格函数

    def set_price_source(self, func: Callable) -> None:
        """注入价格获取函数 func(symbol) -> price"""
        self._price_source = func

    def send_order(self, order: Order) -> bool:
        order.status = OrderStatus.PENDING
        self._pending_orders.append(order)
        self._try_fill(order)
        return True

    def cancel_order(self, order_id: str) -> bool:
        for o in self._pending_orders:
            if o.order_id == order_id and o.status == OrderStatus.PENDING:
                o.status = OrderStatus.CANCELLED
                return True
        return False

    def get_fills(self) -> list[Fill]:
        fills = self._fills[:]
        self._fills.clear()
        return fills

    def get_position(self, symbol: str) -> float:
        return 0.0  # 模拟器不维护持仓，由 Account 维护

    def _try_fill(self, order: Order) -> None:
        import random

        if random.random() > self.fill_probability:
            return

        if self._price_source is None:
            return

        base_price = self._price_source(order.symbol)
        if base_price is None:
            return

        # 滑点：买入更贵，卖出更便宜
        slip = base_price * self.slippage
        fill_price = base_price + slip if order.direction == Direction.BUY else base_price - slip

        # 佣金
        notional = order.signal.quantity * fill_price
        commission = max(notional * self.commission_rate, self.min_commission)

        fill = Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.signal.quantity,
            price=round(fill_price, 3),
            commission=round(commission, 2),
            timestamp=datetime.now(),
        )
        order.filled_quantity = order.signal.quantity
        order.filled_price = fill_price
        order.status = OrderStatus.FILLED
        self._fills.append(fill)
