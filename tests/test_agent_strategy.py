"""AgentStrategy 回测对接测试."""

import pandas as pd

from investment_agent.core.types import Account, Context, Direction, Signal
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.base import EventType
from investment_agent.skills.base import SkillResult
from investment_agent.strategy.agent_strategy import AgentStrategy


class DummySkill:
    """模拟 Skill，在价格变动超过阈值时返回 BUY 信号."""

    def __init__(self):
        self.name = "DummySkill"
        self.description = "test"
        self.priority = 0
        self._enabled = True

    def is_enabled(self):
        return self._enabled

    def execute(self, event, context=None):
        if event.event_type == EventType.PRICE_ALERT:
            return SkillResult(
                skill_name=self.name,
                signals=[
                    Signal(
                        symbol=event.symbol or "000001.SZ",
                        direction=Direction.BUY,
                        quantity=100,
                        price=10.0,
                        confidence=0.8,
                        reason="test",
                    )
                ],
                confidence=0.8,
                reasoning="test",
            )
        return SkillResult(skill_name=self.name)


class TestAgentStrategy:
    def _make_data(self, closes: list[float]) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "open": [c * 0.99 for c in closes],
                "high": [c * 1.01 for c in closes],
                "low": [c * 0.98 for c in closes],
                "close": closes,
                "volume": [10000] * len(closes),
            },
            index=pd.date_range("2024-01-01", periods=len(closes)),
        )
        df.attrs["symbol"] = "000001.SZ"
        return df

    def test_no_signal_when_change_below_threshold(self) -> None:
        orch = AgentOrchestrator()
        strat = AgentStrategy(orchestrator=orch, price_change_threshold=2.0)
        data = self._make_data([10.0, 10.05, 10.1])  # 变动 < 2%
        ctx = Context(account=Account())
        signals = strat.generate_signals(data, ctx)
        assert signals == []

    def test_generates_signal_on_large_change(self) -> None:
        orch = AgentOrchestrator()
        skill = DummySkill()
        orch.register_skill(skill)
        strat = AgentStrategy(orchestrator=orch, price_change_threshold=2.0)
        data = self._make_data([10.0, 10.5, 11.0])  # +10% > 2%
        ctx = Context(account=Account())
        signals = strat.generate_signals(data, ctx)
        assert len(signals) == 1
        assert signals[0].direction == Direction.BUY
        assert signals[0].symbol == "000001.SZ"

    def test_empty_data(self) -> None:
        orch = AgentOrchestrator()
        strat = AgentStrategy(orchestrator=orch)
        data = pd.DataFrame()
        ctx = Context(account=Account())
        assert strat.generate_signals(data, ctx) == []

    def test_records_last_price(self) -> None:
        orch = AgentOrchestrator()
        skill = DummySkill()
        orch.register_skill(skill)
        strat = AgentStrategy(orchestrator=orch, price_change_threshold=2.0)
        data = self._make_data([10.0, 10.5, 11.0])
        ctx = Context(account=Account())
        strat.generate_signals(data, ctx)
        assert strat._last_price.get("000001.SZ") == 11.0
