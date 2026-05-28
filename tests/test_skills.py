"""TDD: Skill 系统测试."""

from investment_agent.core.types import Direction
from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.skills.base import SkillResult
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill


class MockLLM:
    """Mock LLM for testing."""

    def __init__(self, response: dict | None = None):
        self.response = response or {
            "sentiment": "positive",
            "sentiment_score": 0.8,
            "impact_level": "high",
            "affected_sectors": ["新能源"],
            "summary": "利好消息",
            "trading_signal": "buy",
            "confidence": 0.9,
        }

    def analyze_news(self, **kwargs):
        return self.response

    def chat(self, **kwargs):
        from investment_agent.llm.adapter import LLMResponse

        return LLMResponse(content=str(self.response))

    def _parse_json_response(self, text):
        return self.response

    def _msg(self, role, content):
        from investment_agent.llm.adapter import LLMMessage

        return LLMMessage(role=role, content=content)


class TestNewsAnalysisSkill:
    def test_execute_generates_buy_signal(self):
        mock_llm = MockLLM()
        skill = NewsAnalysisSkill(llm=mock_llm)
        event = MarketEvent(
            event_type=EventType.NEWS,
            title="Good News",
            content="Company profits surged",
            symbol="000001.SZ",
        )
        result = skill.execute(event)
        assert result.skill_name == "NewsAnalysisSkill"
        assert result.confidence == 0.9
        assert len(result.signals) == 1
        assert result.signals[0].direction == Direction.BUY

    def test_execute_no_signal_when_low_confidence(self):
        mock_llm = MockLLM(
            response={
                "sentiment": "neutral",
                "sentiment_score": 0.1,
                "impact_level": "low",
                "trading_signal": "hold",
                "confidence": 0.3,
            }
        )
        skill = NewsAnalysisSkill(llm=mock_llm)
        event = MarketEvent(event_type=EventType.NEWS, title="Minor News", content="...")
        result = skill.execute(event)
        assert len(result.signals) == 0


class TestPortfolioAdvisorSkill:
    def test_execute_with_no_context(self):
        skill = PortfolioAdvisorSkill()
        event = MarketEvent(event_type=EventType.NEWS, title="Test", content="Test")
        result = skill.execute(event)
        assert "No context" in result.reasoning

    def test_execute_synthesizes_signals(self):
        skill = PortfolioAdvisorSkill(
            llm=MockLLM(
                {
                    "final_signal": "buy",
                    "symbol": "000001.SZ",
                    "position_pct": 0.1,
                    "confidence": 0.8,
                    "reasoning": "综合看好",
                }
            )
        )
        event = MarketEvent(
            event_type=EventType.NEWS, title="Test", content="Test", symbol="000001.SZ"
        )
        sr1 = SkillResult(skill_name="News", signals=[], confidence=0.7)
        result = skill.execute(event, {"skill_results": [sr1]})
        assert len(result.signals) == 1
        assert result.signals[0].direction == Direction.BUY
