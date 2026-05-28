"""传感器基类 —— 金融事件感知层.

传感器负责从外部世界捕获信息，生成标准化的 MarketEvent.
参考 TradingAgents-CN 的舆情监控 Agent 设计.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    NEWS = "news"
    EARNINGS = "earnings"
    MACRO = "macro"
    POLICY = "policy"
    SOCIAL = "social"
    PRICE_ALERT = "price_alert"


@dataclass
class MarketEvent:
    """标准化市场事件."""

    event_type: EventType
    title: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str | None = None  # 关联标的
    source: str = ""  # 来源: 新浪财经/东方财富/公告/微博
    url: str = ""  # 原文链接
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """转换为 LLM 可读的文本格式."""
        lines = [
            f"[事件类型] {self.event_type.value}",
            f"[标题] {self.title}",
            f"[时间] {self.timestamp.isoformat()}",
        ]
        if self.symbol:
            lines.append(f"[标的] {self.symbol}")
        if self.source:
            lines.append(f"[来源] {self.source}")
        lines.append(f"[内容] {self.content}")
        return "\n".join(lines)


class Sensor(ABC):
    """传感器抽象基类."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__

    @abstractmethod
    def poll(self) -> list[MarketEvent]:
        """轮询获取新事件."""
        pass

    def subscribe(self, callback: Callable) -> None:  # noqa: ANN001, B027
        """订阅事件回调（用于实时推送模式）."""
        pass
