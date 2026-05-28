"""Mock Skill —— 用于回测和模拟盘快速验证，不调用 LLM.

根据事件关键词快速返回预设信号，适合：
- 回测框架对接验证
- 模拟盘快速跑通
- CI 自动化测试
"""

from __future__ import annotations

from typing import Any

from investment_agent.core.types import Direction, Signal
from investment_agent.sensors.base import MarketEvent
from investment_agent.skills.base import Skill, SkillResult


class MockAgentSkill(Skill):
    """快速 Mock Skill.

    规则:
    - 标题含 "涨" / "利好" / "突破" / "增长" → BUY
    - 标题含 "跌" / "利空" / "下降" / "衰退" → SELL
    - 其他 → HOLD (不返回信号)
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(
            name="MockAgentSkill",
            description="Fast mock skill for backtest/paper trading",
            priority=priority,
        )

    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        title = event.title.lower()
        content = event.content.lower()
        text = title + " " + content

        buy_keywords = ["涨", "利好", "突破", "增长", "上升", "强势", "大涨", "反弹"]
        sell_keywords = ["跌", "利空", "下降", "衰退", "下跌", "弱势", "大跌", "回调"]

        if any(k in text for k in buy_keywords):
            direction = Direction.BUY
            confidence = 0.75
            reason = f"[Mock] 检测到利好关键词: {event.title}"
        elif any(k in text for k in sell_keywords):
            direction = Direction.SELL
            confidence = 0.65
            reason = f"[Mock] 检测到利空关键词: {event.title}"
        else:
            return SkillResult(
                skill_name=self.name,
                reasoning=f"[Mock] 无明确方向: {event.title}",
                confidence=0.3,
            )

        # 价格从 event metadata 或 context 中获取
        price = 10.0
        if event.metadata and "close" in event.metadata:
            price = float(event.metadata["close"])
        elif context and "current_prices" in context:
            price = float(context["current_prices"].get(event.symbol or "", 10.0))

        signal = Signal(
            symbol=event.symbol or "000001.SZ",
            direction=direction,
            quantity=100,
            price=price,
            confidence=confidence,
            reason=reason,
        )
        return SkillResult(
            skill_name=self.name,
            signals=[signal],
            confidence=confidence,
            reasoning=reason,
        )
