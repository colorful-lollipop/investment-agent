"""AKShare 传感器测试."""

from unittest.mock import MagicMock, patch

from investment_agent.sensors.akshare_sensor import AKShareDataSensor
from investment_agent.sensors.base import EventType


class TestAKShareDataSensor:
    def test_init(self) -> None:
        sensor = AKShareDataSensor(symbols=["300750.SZ"], limit=5)
        assert sensor.name == "AKShareDataSensor"
        assert sensor.symbols == ["300750.SZ"]
        assert sensor.limit == 5

    def test_poll_empty_when_no_data(self) -> None:
        """akshare 异常时返回空列表，不崩溃."""
        sensor = AKShareDataSensor()
        with patch("akshare.stock_news_em", side_effect=Exception("network")):
            events = sensor.poll()
        assert events == []

    def test_poll_news_parsing(self) -> None:
        """测试新闻解析和去重."""
        sensor = AKShareDataSensor(symbols=["300750.SZ"], limit=2)
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.head.return_value.iterrows.return_value = [
            (
                0,
                {
                    "新闻标题": "测试标题",
                    "新闻内容": "测试内容",
                    "发布时间": "2026-05-27 10:00:00",
                    "文章来源": "测试来源",
                    "新闻链接": "http://test.com",
                },
            ),
        ]

        with patch("akshare.stock_news_em", return_value=mock_df):
            events = sensor._poll_news()

        assert len(events) == 1
        assert events[0].event_type == EventType.NEWS
        assert events[0].title == "测试标题"
        assert events[0].symbol == "300750.SZ"

    def test_deduplication(self) -> None:
        """相同新闻不应重复返回."""
        sensor = AKShareDataSensor(symbols=["300750.SZ"], limit=2)
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.head.return_value.iterrows.return_value = [
            (
                0,
                {
                    "新闻标题": "相同新闻",
                    "新闻内容": "内容",
                    "发布时间": "2026-05-27 10:00:00",
                    "文章来源": "来源",
                    "新闻链接": "http://same.com",
                },
            ),
            (
                1,
                {
                    "新闻标题": "相同新闻",
                    "新闻内容": "内容",
                    "发布时间": "2026-05-27 10:00:00",
                    "文章来源": "来源",
                    "新闻链接": "http://same.com",
                },
            ),
        ]

        with patch("akshare.stock_news_em", return_value=mock_df):
            events1 = sensor._poll_news()
            events2 = sensor._poll_news()

        assert len(events1) == 1
        assert len(events2) == 0  # 第二次应去重
