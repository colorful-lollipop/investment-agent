"""Skill 系统 —— Agent 的可扩展能力插件.

设计参考 Semantic Kernel 和 OpenAI Swarm 的 Skill/Tool 概念:
- 每个 Skill 是一个独立的金融分析能力单元
- Skill 可调用 LLM、数据源、计算工具
- Skill 之间可以组合和链式调用
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from investment_agent.core.types import Signal
from investment_agent.sensors.base import MarketEvent


@dataclass
class SkillResult:
    """Skill 执行结果."""

    skill_name: str
    signals: list[Signal] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""  # LLM 的推理过程（可解释性）
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def has_signals(self) -> bool:
        return len(self.signals) > 0


class Skill(ABC):
    """Skill 抽象基类.

    每个 Skill 接收 MarketEvent，输出 SkillResult（包含交易信号和分析报告）.
    """

    def __init__(self, name: str = "", description: str = "") -> None:
        self.name = name or self.__class__.__name__
        self.description = description
        self._enabled = True

    @abstractmethod
    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        """执行 Skill，分析事件并生成交易信号.

        Args:
            event: 市场事件
            context: 额外上下文（当前持仓、账户状态、历史数据等）

        Returns:
            SkillResult: 分析结果和交易信号
        """
        pass

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
