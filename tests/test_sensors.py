"""TDD: 传感器层测试."""

from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.sensors.macro_sensor import MacroSensor
from investment_agent.sensors.news_sensor import NewsSensor


class TestMarketEvent:
    def test_to_prompt_text(self):
        event = MarketEvent(
            event_type=EventType.NEWS,
            title="Test News",
            content="Something happened",
            symbol="000001.SZ",
            source="TestSource",
        )
        text = event.to_prompt_text()
        assert "[事件类型] news" in text
        assert "[标题] Test News" in text
        assert "[标的] 000001.SZ" in text


class TestNewsSensor:
    def test_get_mock_events(self):
        sensor = NewsSensor()
        events = sensor.get_mock_events()
        assert len(events) >= 3
        assert all(e.event_type == EventType.NEWS for e in events)

    def test_poll_returns_list(self):
        sensor = NewsSensor()
        events = sensor.poll()
        assert isinstance(events, list)


class TestMacroSensor:
    def test_get_mock_events(self):
        sensor = MacroSensor()
        events = sensor.get_mock_events()
        assert len(events) >= 2
        assert any(e.event_type == EventType.MACRO for e in events)
