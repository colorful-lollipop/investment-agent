"""宏观分析 Skill —— 分析宏观经济事件对市场的系统性影响."""

from __future__ import annotations

from typing import Any

from investment_agent.llm.adapter import LLMAdapter
from investment_agent.sensors.base import MarketEvent
from investment_agent.skills.base import Skill, SkillResult


class MacroAnalysisSkill(Skill):
    """宏观分析 Skill.

    分析央行政策、宏观经济数据对市场的系统性影响，
    输出板块配置建议和大盘择时信号.
    """

    def __init__(self, llm: LLMAdapter | None = None, priority: int = 0) -> None:
        super().__init__(
            name="MacroAnalysisSkill",
            description="Analyze macroeconomic events and policy impacts",
            priority=priority,
        )
        self.llm = llm or LLMAdapter()

    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        """分析宏观事件."""
        prompt = (
            f"你是一位宏观经济学家。请分析以下宏观事件对市场的影响:\n\n"
            f"{event.to_prompt_text()}\n\n"
            f"请输出 JSON 格式:\n"
            f"{{\n"
            f'  "market_impact": "bullish|bearish|neutral",\n'
            f'  "affected_sectors": ["受益板块", "受损板块"],\n'
            f'  "position_advice": "increase|decrease|maintain",\n'
            f'  "confidence": 0.0,\n'
            f'  "reasoning": "分析逻辑"\n'
            f"}}"
        )

        resp = self.llm.chat(
            messages=[
                self._msg("system", "你是宏观经济学家，输出严格JSON格式。"),
                self._msg("user", prompt),
            ]
        )
        analysis = LLMAdapter._parse_json_response(resp.content)

        return SkillResult(
            skill_name=self.name,
            signals=[],
            analysis=analysis,
            reasoning=analysis.get("reasoning", ""),
            confidence=analysis.get("confidence", 0.0),
        )

    def _msg(self, role: str, content: str) -> Any:
        from investment_agent.llm.adapter import LLMMessage

        return LLMMessage(role=role, content=content)
