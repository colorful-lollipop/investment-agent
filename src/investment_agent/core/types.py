"""核心领域模型 —— 量化交易系统的通用语言
设计原则：不可变值对象 + 显式状态 + 可审计
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Direction(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass(frozen=True)
class Signal:
    """策略生成的交易信号 —— 只表达意图，不涉及执行细节"""

    symbol: str
    direction: Direction
    quantity: float  # 目标数量，正数
    price: float | None  # 目标限价，None 表示市价
    confidence: float = 0.5  # 0~1
    reason: str = ""  # 可解释性：为什么产生这个信号
    strategy: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")


@dataclass
class Order:
    """经过风控审核后的可执行订单"""

    signal: Signal
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def symbol(self) -> str:
        return self.signal.symbol

    @property
    def direction(self) -> Direction:
        return self.signal.direction

    @property
    def remaining_quantity(self) -> float:
        return self.signal.quantity - self.filled_quantity


@dataclass
class Fill:
    """成交回报"""

    order_id: str
    symbol: str
    direction: Direction
    quantity: float
    price: float
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    """持仓快照"""

    symbol: str
    quantity: float = 0.0  # 正=多头，负=空头（如支持做空）
    avg_cost: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    last_price: float | None = None

    def update_market_price(self, price: float) -> None:
        self.last_price = price
        self.market_value = self.quantity * price
        if self.quantity != 0:
            self.unrealized_pnl = self.market_value - (self.quantity * self.avg_cost)

    @property
    def return_pct(self) -> float:
        if self.avg_cost == 0 or self.quantity == 0:
            return 0.0
        return (self.last_price - self.avg_cost) / self.avg_cost if self.last_price else 0.0


@dataclass
class Account:
    """账户快照"""

    cash: float = 1_000_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    total_value_history: list[tuple[datetime, float]] = field(default_factory=list)

    @property
    def total_value(self) -> float:
        pos_value = sum(p.market_value for p in self.positions.values())
        return self.cash + pos_value

    @property
    def total_position_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    def get_position(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def record_snapshot(self, timestamp: datetime | None = None) -> None:
        ts = timestamp or datetime.now()
        self.total_value_history.append((ts, self.total_value))

    def apply_fill(self, fill: Fill) -> None:
        """根据成交回报更新账户资金和持仓"""
        cost = fill.quantity * fill.price + fill.commission
        pos = self.get_position(fill.symbol)

        if fill.direction == Direction.BUY:
            self.cash -= cost
            # 更新平均成本
            total_cost = pos.avg_cost * pos.quantity + fill.quantity * fill.price
            pos.quantity += fill.quantity
            pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0.0
        else:  # SELL
            self.cash += fill.quantity * fill.price - fill.commission
            pos.quantity -= fill.quantity
            if pos.quantity <= 0:
                pos.avg_cost = 0.0
                pos.quantity = 0.0

        if pos.last_price:
            pos.update_market_price(pos.last_price)


@dataclass
class Portfolio:
    """组合视图"""

    account: Account
    current_prices: dict[str, float] = field(default_factory=dict)

    def weight(self, symbol: str) -> float:
        tv = self.account.total_value
        if tv == 0:
            return 0.0
        pos = self.account.positions.get(symbol)
        return (pos.market_value / tv) if pos else 0.0

    @property
    def max_drawdown(self) -> float:
        if not self.account.total_value_history:
            return 0.0
        peak = 0.0
        max_dd = 0.0
        for _, val in self.account.total_value_history:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd


@dataclass
class Context:
    """策略运行时上下文 —— 包含当前账户、历史数据、配置参数"""

    account: Account
    current_time: datetime = field(default_factory=datetime.now)
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
