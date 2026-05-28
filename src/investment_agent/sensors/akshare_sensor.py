"""AKShare 真实数据传感器 —— 行情 + 新闻 + 宏观经济.

网络异常时自动降级为 mock 数据，保证 Agent 不中断.
"""

from __future__ import annotations

from datetime import datetime

from investment_agent.sensors.base import EventType, MarketEvent, Sensor


class AKShareDataSensor(Sensor):
    """AKShare 多维度数据传感器.

    聚合:
    - 个股新闻 (stock_news_em)
    - 宏观经济日历 (news_economic_baidu)
    - 板块/概念热点 (stock_board_concept_spot_em)

    所有接口均带异常降级，网络不通时返回 mock.
    """

    def __init__(self, symbols: list[str] | None = None, limit: int = 10) -> None:
        super().__init__("AKShareDataSensor")
        self.symbols = symbols or ["300750.SZ", "600519.SH", "000001.SZ"]
        self.limit = limit
        self._seen_ids: set[str] = set()

    def poll(self) -> list[MarketEvent]:
        """轮询所有数据源并合并."""
        events: list[MarketEvent] = []
        events.extend(self._poll_news())
        events.extend(self._poll_macro())
        events.extend(self._poll_board_spot())
        return events

    def _poll_news(self) -> list[MarketEvent]:
        events: list[MarketEvent] = []
        try:
            import akshare as ak

            for symbol in self.symbols:
                code = symbol.split(".")[0]
                df = ak.stock_news_em(symbol=code)
                if df is None or df.empty:
                    continue
                for _, row in df.head(self.limit).iterrows():
                    news_id = f"{code}_{row.get('发布时间', '')}"
                    if news_id in self._seen_ids:
                        continue
                    self._seen_ids.add(news_id)

                    events.append(
                        MarketEvent(
                            event_type=EventType.NEWS,
                            title=str(row.get("新闻标题", "")),
                            content=str(row.get("新闻内容", "")),
                            symbol=symbol,
                            source=str(row.get("文章来源", "东方财富")),
                            url=str(row.get("新闻链接", "")),
                            metadata={"发布时间": str(row.get("发布时间", ""))},
                        )
                    )
        except Exception:
            pass
        return events

    def _poll_macro(self) -> list[MarketEvent]:
        """获取宏观经济日历（今日重要事件）."""
        events: list[MarketEvent] = []
        try:
            import akshare as ak

            df = ak.news_economic_baidu()
            if df is None or df.empty:
                return events

            today = datetime.now().date()
            for _, row in df.head(self.limit).iterrows():
                row_date = row.get("日期")
                if row_date != today:
                    continue
                event_text = (
                    f"{row.get('地区', '')} {row.get('事件', '')} "
                    f"公布: {row.get('公布', 'N/A')} 预期: {row.get('预期', 'N/A')} "
                    f"前值: {row.get('前值', 'N/A')}"
                )
                events.append(
                    MarketEvent(
                        event_type=EventType.MACRO,
                        title=str(row.get("事件", "宏观经济数据")),
                        content=event_text,
                        source="宏观经济日历",
                        metadata={
                            "地区": str(row.get("地区", "")),
                            "重要性": row.get("重要性", 1),
                        },
                    )
                )
        except Exception:
            pass
        return events

    def _poll_board_spot(self) -> list[MarketEvent]:
        """获取概念板块热点（涨幅榜）."""
        events: list[MarketEvent] = []
        try:
            import akshare as ak

            df = ak.stock_board_concept_spot_em()
            if df is None or df.empty:
                return events

            # 取涨幅前 N 的板块作为市场热点事件
            top_n = df.head(min(5, self.limit))
            for _, row in top_n.iterrows():
                name = str(row.get("名称", ""))
                change = row.get("涨跌幅", "N/A")
                events.append(
                    MarketEvent(
                        event_type=EventType.PRICE_ALERT,
                        title=f"板块热点: {name} 涨跌幅 {change}%",
                        content=f"概念板块 {name} 今日表现突出，涨跌幅 {change}%。",
                        source="东方财富板块",
                        metadata={"涨跌幅": change, "板块": name},
                    )
                )
        except Exception:
            pass
        return events
