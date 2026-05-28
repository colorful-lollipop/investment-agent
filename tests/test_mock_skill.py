"""MockAgentSkill 测试."""

from investment_agent.core.types import Direction
from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.skills.mock_skill import MockAgentSkill


class TestMockAgentSkill:
    def test_buy_signal(self) -> None:
        skill = MockAgentSkill()
        event = MarketEvent(
            event_type=EventType.NEWS,
            title="股价大涨突破新高",
            content="公司业绩超预期，股价大涨",
            source="测试",
        )
        result = skill.execute(event)
        assert result.has_signals()
        assert result.signals[0].direction == Direction.BUY

    def test_sell_signal(self) -> None:
        skill = MockAgentSkill()
        event = MarketEvent(
            event_type=EventType.NEWS,
            title="股价大跌回调",
            content="市场恐慌，股价大跌",
            source="测试",
        )
        result = skill.execute(event)
        assert result.has_signals()
        assert result.signals[0].direction == Direction.SELL

    def test_hold_signal(self) -> None:
        skill = MockAgentSkill()
        event = MarketEvent(
            event_type=EventType.NEWS,
            title="公司发布年报",
            content="业绩符合预期",
            source="测试",
        )
        result = skill.execute(event)
        assert not result.has_signals()

    def test_price_from_metadata(self) -> None:
        skill = MockAgentSkill()
        event = MarketEvent(
            event_type=EventType.PRICE_ALERT,
            title="价格变动大涨 +3%",
            content="测试",
            source="测试",
            metadata={"close": 55.5},
        )
        result = skill.execute(event)
        assert result.has_signals()
        assert result.signals[0].price == 55.5
