"""MultiMarketPriceSensor 测试."""

from investment_agent.sensors.multimarket_sensor import MultiMarketPriceSensor


class TestMultiMarketPriceSensor:
    def test_poll_first_time(self) -> None:
        sensor = MultiMarketPriceSensor(symbols=["AAPL"], change_threshold=0.1)
        events = sensor.poll()
        assert len(events) == 1  # always_emit=False 但 first poll 也返回
        assert events[0].symbol == "AAPL"
        assert events[0].event_type.value == "price_alert"

    def test_poll_no_change(self) -> None:
        sensor = MultiMarketPriceSensor(symbols=["AAPL"], change_threshold=100.0)
        sensor.poll()  # first poll
        events = sensor.poll()  # no significant change
        assert len(events) == 0

    def test_poll_always_emit(self) -> None:
        sensor = MultiMarketPriceSensor(symbols=["AAPL"], change_threshold=100.0, always_emit=True)
        sensor.poll()
        events = sensor.poll()
        assert len(events) == 1
