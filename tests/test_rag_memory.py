"""RAG Memory 测试."""

import tempfile

from investment_agent.memory.rag_memory import RAGMemory
from investment_agent.sensors.base import EventType, MarketEvent


class TestRAGMemory:
    def test_add_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = RAGMemory(persist_dir=tmpdir)
            event = MarketEvent(
                event_type=EventType.NEWS,
                title="央行降准",
                content="央行宣布降准0.5个百分点",
                source="测试",
            )
            mem.add(event)
            stats = mem.get_stats()
            assert stats["count"] == 1

            # 检索相似事件
            query = MarketEvent(
                event_type=EventType.NEWS,
                title="央行再次降准",
                content="央行宣布再次降准",
                source="测试",
            )
            hits = mem.search(query, n_results=3)
            assert len(hits) == 1
            assert hits[0]["metadata"]["title"] == "央行降准"

    def test_add_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = RAGMemory(persist_dir=tmpdir)
            events = [
                MarketEvent(
                    event_type=EventType.NEWS,
                    title=f"新闻{i}",
                    content=f"内容{i}",
                    source="测试",
                )
                for i in range(3)
            ]
            mem.add_batch(events)
            assert mem.get_stats()["count"] == 3

    def test_filter_by_event_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = RAGMemory(persist_dir=tmpdir)
            mem.add(
                MarketEvent(event_type=EventType.NEWS, title="新闻", content="内容", source="测试")
            )
            mem.add(
                MarketEvent(event_type=EventType.MACRO, title="宏观", content="内容", source="测试")
            )

            query = MarketEvent(
                event_type=EventType.NEWS, title="查询", content="查询", source="测试"
            )
            hits = mem.search(query, n_results=5, event_type=EventType.MACRO)
            assert len(hits) == 1
            assert hits[0]["metadata"]["event_type"] == "macro"

    def test_idempotent_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = RAGMemory(persist_dir=tmpdir)
            event = MarketEvent(
                event_type=EventType.NEWS,
                title="唯一新闻",
                content="内容",
                source="测试",
            )
            mem.add(event)
            mem.add(event)
            assert mem.get_stats()["count"] == 1
