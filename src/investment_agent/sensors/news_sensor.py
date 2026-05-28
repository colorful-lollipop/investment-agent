"""新闻传感器 —— 基于 akshare 获取 A 股财经新闻.

参考 FinNews AI 和 TradingAgents-CN 的新闻舆情监控设计.
"""

from __future__ import annotations

from investment_agent.sensors.base import EventType, MarketEvent, Sensor


class NewsSensor(Sensor):
    """A股财经新闻传感器.

    支持数据源:
    - 东方财富财经新闻 (akshare)
    - 新浪财经要闻 (akshare)
    - 个股新闻 (akshare)
    """

    def __init__(self, limit: int = 20) -> None:
        super().__init__("NewsSensor")
        self.limit = limit
        self._seen_ids: set[str] = set()

    def poll(self) -> list[MarketEvent]:
        """轮询获取最新财经新闻."""
        events: list[MarketEvent] = []
        try:
            import akshare as ak

            # 获取东方财富财经新闻
            df = ak.stock_news_em()
            if df is None or df.empty:
                return events

            for _, row in df.head(self.limit).iterrows():
                news_id = str(row.get("url", ""))
                if news_id in self._seen_ids:
                    continue
                self._seen_ids.add(news_id)

                title = str(row.get("title", ""))
                content = str(row.get("content", title))
                event = MarketEvent(
                    event_type=EventType.NEWS,
                    title=title,
                    content=content,
                    source="东方财富",
                    url=str(row.get("url", "")),
                    metadata={"keycode": str(row.get("keycode", ""))},
                )
                events.append(event)
        except Exception:
            # 网络/API 异常时返回空列表，不中断主流程
            pass
        return events

    def poll_symbol_news(self, symbol: str) -> list[MarketEvent]:
        """获取特定标的的新闻."""
        events: list[MarketEvent] = []
        try:
            import akshare as ak

            code = symbol.split(".")[0]
            df = ak.stock_news_main_cx()
            if df is None or df.empty:
                return events

            # 简单过滤：标题或内容包含股票代码/名称
            for _, row in df.head(self.limit).iterrows():
                title = str(row.get("title", ""))
                content = str(row.get("content", ""))
                if code not in title and code not in content:
                    continue

                event = MarketEvent(
                    event_type=EventType.NEWS,
                    title=title,
                    content=content,
                    symbol=symbol,
                    source="财联社",
                    url=str(row.get("url", "")),
                )
                events.append(event)
        except Exception:
            pass
        return events

    def get_mock_events(self) -> list[MarketEvent]:
        """返回模拟新闻事件（用于测试和演示）."""
        return [
            MarketEvent(
                event_type=EventType.NEWS,
                title="央行宣布降准0.5个百分点，释放流动性约1万亿元",
                content="中国人民银行决定于近期下调金融机构存款准备金率0.5个百分点，"
                "不含已执行5%存款准备金率的金融机构。此次降准预计释放长期资金约1万亿元。",
                source="模拟数据",
                symbol="000001.SZ",
            ),
            MarketEvent(
                event_type=EventType.NEWS,
                title="某新能源车企发布超预期季度财报，营收同比增长120%",
                content="公司Q3营收达到500亿元，同比增长120%，净利润率提升至15%。"
                "管理层上调全年交付指引至200万辆。",
                source="模拟数据",
                symbol="600519.SH",
            ),
            MarketEvent(
                event_type=EventType.NEWS,
                title="美国宣布对华加征关税，涉及半导体和新能源领域",
                content="美国贸易代表办公室宣布对价值约180亿美元的中国进口商品加征关税，"
                "主要针对半导体、太阳能电池和电动汽车。",
                source="模拟数据",
            ),
        ]
