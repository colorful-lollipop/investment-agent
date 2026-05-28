"""多市场价格传感器 —— A股/港股/美股统一监控.

使用 UnifiedDataProvider 获取实时价格，生成 PRICE_ALERT 事件.
支持批量查询，降低网络开销.
"""

from __future__ import annotations

from investment_agent.data.unified_provider import UnifiedDataProvider
from investment_agent.sensors.base import EventType, MarketEvent, Sensor


class MultiMarketPriceSensor(Sensor):
    """多市场价格传感器.

    定时轮询一组标的的最新价格，生成 PRICE_ALERT 事件.
    当 always_emit=True 时，每次 poll 都返回事件（用于持续分析）.
    """

    def __init__(
        self,
        symbols: list[str],
        provider: UnifiedDataProvider | None = None,
        change_threshold: float = 1.0,
        always_emit: bool = False,
    ) -> None:
        super().__init__("MultiMarketPriceSensor")
        self.symbols = symbols
        self.provider = provider or UnifiedDataProvider()
        self.change_threshold = change_threshold
        self.always_emit = always_emit
        self._last_prices: dict[str, float] = {}

    def poll(self) -> list[MarketEvent]:
        """轮询价格并生成事件."""
        events: list[MarketEvent] = []
        prices = self.provider.get_batch_prices(self.symbols)

        for sym, price in prices.items():
            last = self._last_prices.get(sym)
            self._last_prices[sym] = price

            change_pct = 0.0
            if last and last > 0:
                change_pct = (price - last) / last * 100

            # 只有在价格变动超过阈值或 always_emit 时才生成事件
            if (
                not self.always_emit
                and last is not None
                and abs(change_pct) < self.change_threshold
            ):
                continue

            direction = "上涨" if change_pct > 0 else "下跌" if change_pct < 0 else "持平"
            events.append(
                MarketEvent(
                    event_type=EventType.PRICE_ALERT,
                    title=f"{sym} 最新价 {price:.2f} ({direction})",
                    content=(
                        f"最新价: {price:.2f}, 上一价: {last or price:.2f}, "
                        f"变动: {change_pct:+.2f}%"
                    ),
                    symbol=sym,
                    source="UnifiedDataProvider",
                    metadata={
                        "price": price,
                        "last_price": last,
                        "change_pct": change_pct,
                    },
                )
            )
        return events
