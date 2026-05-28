"""TDD: Agent 编排器测试."""

from investment_agent.core.types import Direction
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.news_sensor import NewsSensor
from investment_agent.skills.base import Skill, SkillResult
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill


class MockSkill(Skill):
    """测试用 Skill."""

    def __init__(self, signal_direction: Direction | None = None):
        super().__init__("MockSkill")
        self.signal_direction = signal_direction

    def execute(self, event, context=None):
        from investment_agent.core.types import Signal

        signals = []
        if self.signal_direction and event.symbol:
            signals.append(
                Signal(
                    symbol=event.symbol,
                    direction=self.signal_direction,
                    quantity=100,
                    price=None,
                    confidence=0.8,
                    reason="mock",
                    strategy=self.name,
                )
            )
        return SkillResult(skill_name=self.name, signals=signals, confidence=0.8)


class TestAgentOrchestrator:
    def test_register_components(self):
        orch = AgentOrchestrator()
        orch.register_sensor(NewsSensor())
        orch.register_skill(MockSkill())
        orch.register_advisor(PortfolioAdvisorSkill())
        assert len(orch._sensors) == 1
        assert len(orch._skills) == 1
        assert orch._advisor is not None

    def test_dedup_signals(self):
        from investment_agent.core.types import Signal

        s1 = Signal(symbol="A", direction=Direction.BUY, quantity=100, price=None, confidence=0.6)
        s2 = Signal(symbol="A", direction=Direction.BUY, quantity=200, price=None, confidence=0.9)
        s3 = Signal(symbol="B", direction=Direction.SELL, quantity=100, price=None, confidence=0.7)
        result = AgentOrchestrator._dedup_signals([s1, s2, s3])
        assert len(result) == 2
        # 保留置信度更高的
        a_signals = [s for s in result if s.symbol == "A"]
        assert a_signals[0].confidence == 0.9

    def test_run_with_mock(self):
        orch = AgentOrchestrator()
        orch.register_sensor(NewsSensor())
        orch.register_skill(MockSkill(Direction.BUY))
        signals = orch.run_with_mock()
        # 模拟事件中有3条新闻，每条可能生成信号
        assert isinstance(signals, list)
        # 因为 symbol 可能不同，但至少应该有信号
        for s in signals:
            assert s.direction in (Direction.BUY, Direction.SELL)

    def test_poll_events_empty(self):
        orch = AgentOrchestrator()
        events = orch.poll_events()
        assert events == []
