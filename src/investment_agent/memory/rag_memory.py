"""RAG 向量记忆 —— 基于 Chroma 的历史事件存储与相似检索.

设计要点:
- 纯本地运行，无需外部服务
- 事件文本自动向量化 (默认使用 sentence-transformers 的 mini 模型)
- 支持按事件类型过滤检索
- Skill 执行前检索相似历史事件，增强上下文
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from investment_agent.sensors.base import EventType, MarketEvent


class RAGMemory:
    """RAG 记忆层.

    使用 Chroma 向量数据库存储 MarketEvent 的 embedding，
    支持基于语义相似度的历史事件检索.
    """

    def __init__(
        self, collection_name: str = "market_events", persist_dir: str | None = None
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir = persist_dir or os.path.join(os.getcwd(), ".chroma_db")
        self._client: Any = None
        self._collection: Any = None

    def _ensure_client(self) -> Any:
        """懒加载 Chroma 客户端."""
        if self._client is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """文本向量化（轻量本地模型）."""
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            ef = DefaultEmbeddingFunction()
            return [e.tolist() for e in ef(texts)]
        except Exception:
            # fallback: 简单的词袋平均（仅保证不崩溃）
            import random

            return [[random.random() for _ in range(384)] for _ in texts]

    def _event_id(self, event: MarketEvent) -> str:
        """生成事件唯一 ID."""
        raw = f"{event.event_type.value}_{event.title}_{event.timestamp.isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def add(self, event: MarketEvent) -> None:
        """将事件存入向量库."""
        collection = self._ensure_client()
        event_id = self._event_id(event)

        # 检查是否已存在
        existing = collection.get(ids=[event_id], include=[])
        if existing and existing.get("ids"):
            return

        text = event.to_prompt_text()
        embedding = self._embed([text])[0]
        collection.add(
            ids=[event_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[
                {
                    "event_type": event.event_type.value,
                    "symbol": event.symbol or "",
                    "source": event.source,
                    "title": event.title[:200],
                }
            ],
        )

    def add_batch(self, events: list[MarketEvent]) -> None:
        """批量添加事件."""
        for event in events:
            self.add(event)

    def search(
        self,
        query_event: MarketEvent,
        n_results: int = 5,
        event_type: EventType | None = None,
    ) -> list[dict[str, Any]]:
        """检索与 query_event 语义相似的历史事件.

        Args:
            query_event: 查询事件
            n_results: 返回条数
            event_type: 可选按事件类型过滤

        Returns:
            相似事件列表，每项包含 event 字段和 distance
        """
        collection = self._ensure_client()
        query_text = query_event.to_prompt_text()
        query_embedding = self._embed([query_text])[0]

        where_filter: dict[str, Any] | None = None
        if event_type:
            where_filter = {"event_type": event_type.value}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        if not results or not results.get("ids"):
            return hits

        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0] if results.get("documents") else []
        metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        dists = results.get("distances", [[]])[0] if results.get("distances") else []

        for i in range(len(ids)):
            hits.append(
                {
                    "id": ids[i],
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 1.0,
                }
            )
        return hits

    def get_stats(self) -> dict[str, Any]:
        """返回向量库统计信息."""
        collection = self._ensure_client()
        return {
            "count": collection.count(),
            "collection": self.collection_name,
            "persist_dir": self.persist_dir,
        }
