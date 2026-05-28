"""Agent 策略 —— 将 AI Agent 编排器接入回测引擎.

每个 bar 上把价格数据包装为 MarketEvent，触发 AgentOrchestrator 生成交易信号.
支持阈值过滤：只在价格变动超过阈值时调用 Agent，减少 LLM 调用次数.
"""

from __future__ import annotations

import logging

import pandas as pd

from investment_agent.core.types import Context, Signal
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.strategy.base import BaseStrategy

logger = logging.getLogger("AgentStrategy")


class AgentStrategy(BaseStrategy):
    """Agent 驱动策略.

    将 AgentOrchestrator 包装为 BaseStrategy，在回测引擎的每个 bar 上:
    1. 检测价格变动是否超过阈值
    2. 构造 MarketEvent（价格变动事件）
    3. 调用 AgentOrchestrator 分析并生成 Signal
    4. 返回 Signal 列表给回测引擎
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        price_change_threshold: float = 2.0,
        name: str = "AgentStrategy",
    ) -> None:
        super().__init__(name=name)
        self.orchestrator = orchestrator
        self.price_change_threshold = price_change_threshold
        self._last_price: dict[str, float] = {}

    def generate_signals(self, data: pd.DataFrame, context: Context) -> list[Signal]:
        """基于当前 bar 数据生成信号."""
        symbol = str(data.attrs.get("symbol", ""))
        if data.empty or len(data) < 2:
            return []

        latest = data.iloc[-1]
        prev = data.iloc[-2]
        close = float(latest["close"])
        prev_close = float(prev["close"])
        change_pct = (close - prev_close) / prev_close * 100

        self._last_price[symbol] = close

        # 只在价格变动超过阈值时触发 Agent（回测中减少 LLM 调用）
        if abs(change_pct) < self.price_change_threshold:
            return []

        event = MarketEvent(
            event_type=EventType.PRICE_ALERT,
            title=f"{symbol} 价格变动 {change_pct:+.2f}%",
            content=(
                f"日期: {latest.name}, 开盘: {float(latest['open']):.2f}, "
                f"收盘: {close:.2f}, 最高: {float(latest['high']):.2f}, "
                f"最低: {float(latest['low']):.2f}, 成交量: {float(latest['volume']):.0f}, "
                f"涨跌幅: {change_pct:.2f}%"
            ),
            symbol=symbol,
            source="回测价格数据",
            metadata={
                "change_pct": change_pct,
                "close": close,
                "volume": float(latest["volume"]),
                "bar_date": str(latest.name),
            },
        )

        try:
            skill_results = self.orchestrator.analyze_event(event)
            signals = self.orchestrator.synthesize(event, skill_results)
            if signals:
                logger.info(
                    "AgentStrategy[%s] generated %d signals on %s",
                    symbol,
                    len(signals),
                    latest.name,
                )
            return signals
        except Exception:
            logger.exception("AgentStrategy failed on %s %s", symbol, latest.name)
            return []
