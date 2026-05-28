"""ReAct Skill 测试."""

from unittest.mock import MagicMock

from investment_agent.core.types import Direction, Signal
from investment_agent.memory.rag_memory import RAGMemory
from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.skills.base import Skill, SkillResult
from investment_agent.skills.react_skill import ReActSkill


class DummySkill(Skill):
    """测试用的虚拟 Skill."""

    def __init__(self, confidence: float = 0.5) -> None:
        super().__init__("DummySkill", "for test")
        self._confidence = confidence
        self.call_count = 0

    def execute(self, event, context=None):
        self.call_count += 1
        return SkillResult(
            skill_name=self.name,
            signals=[
                Signal(
                    symbol="000001.SZ",
                    direction=Direction.BUY,
                    quantity=100,
                    price=10.0,
                    confidence=self._confidence,
                    reason="dummy",
                )
            ],
            confidence=self._confidence,
            reasoning="dummy reasoning",
        )


class TestReActSkill:
    def test_wraps_inner_skill(self) -> None:
        inner = DummySkill(confidence=0.8)
        react = ReActSkill(inner, confidence_threshold=0.5, max_iterations=1)
        event = MarketEvent(event_type=EventType.NEWS, title="测试", content="内容", source="测试")
        result = react.execute(event)
        assert result is not None
        assert len(result.signals) == 1
        assert result.signals[0].direction == Direction.BUY

    def test_reruns_when_low_confidence(self) -> None:
        inner = DummySkill(confidence=0.3)
        react = ReActSkill(inner, confidence_threshold=0.7, max_iterations=2)
        event = MarketEvent(event_type=EventType.NEWS, title="测试", content="内容", source="测试")
        result = react.execute(event)
        # 即使 confidence 低，也应返回 best_result（至少执行了一次）
        assert result.confidence == 0.3
        assert inner.call_count == 2  # 迭代了 2 次

    def test_thought_with_memory(self) -> None:
        inner = DummySkill(confidence=0.8)
        mem = MagicMock(spec=RAGMemory)
        mem.search.return_value = [
            {"metadata": {"event_type": "news", "title": "历史相似"}, "distance": 0.2}
        ]
        react = ReActSkill(inner, memory=mem, confidence_threshold=0.5, max_iterations=1)
        event = MarketEvent(event_type=EventType.NEWS, title="测试", content="内容", source="测试")
        react.execute(event)
        mem.search.assert_called_once()
