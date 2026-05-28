"""投资组合顾问 Skill —— 综合分析多个 Skill 输出，给出最终资产配置建议."""

from __future__ import annotations

from typing import Any

from investment_agent.core.types import Direction, Signal
from investment_agent.llm.adapter import LLMAdapter
from investment_agent.sensors.base import MarketEvent
from investment_agent.skills.base import Skill, SkillResult


class PortfolioAdvisorSkill(Skill):
    """组合顾问 Skill.

    接收多个 Skill 的分析结果，综合评估后生成最终交易信号。
    类似 CrewAI 中的 Process Manager Agent 角色。
    """

    def __init__(self, llm: LLMAdapter | None = None) -> None:
        super().__init__(
            name="PortfolioAdvisorSkill",
            description="Synthesize multiple skill outputs into final trading decisions",
        )
        self.llm = llm or LLMAdapter()

    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        """综合分析上下文中的多个 Skill 结果."""
        if context is None:
            return SkillResult(skill_name=self.name, reasoning="No context provided")

        skill_results: list[SkillResult] = context.get("skill_results", [])
        if not skill_results:
            return SkillResult(skill_name=self.name, reasoning="No skill results to synthesize")

        # 构建综合提示
        prompt_parts = [
            "你是一位投资组合经理。以下是多个分析师对同一事件的分析结果，"
            "请综合评估后给出最终交易决策。",
            "",
            f"原始事件: {event.title}",
            f"事件内容: {event.content[:500]}",
            "",
            "各分析师观点:",
        ]

        for sr in skill_results:
            prompt_parts.append(f"\n--- {sr.skill_name} (置信度: {sr.confidence:.2f}) ---")
            prompt_parts.append(f"推理: {sr.reasoning}")
            prompt_parts.append(f"信号: {[s.direction.name for s in sr.signals]}")
            prompt_parts.append(f"分析: {sr.analysis}")

        prompt_parts.extend(
            [
                "",
                "请输出 JSON 格式:",
                "{",
                '  "final_signal": "buy|sell|hold",',
                '  "symbol": "标的代码",',
                '  "position_pct": 0.0,',
                '  "confidence": 0.0,',
                '  "reasoning": "综合决策理由",',
                '  "risk_warning": "风险提示"',
                "}",
            ]
        )

        from investment_agent.llm.adapter import LLMMessage

        resp = self.llm.chat(
            messages=[
                LLMMessage(role="system", content="你是投资组合经理，输出严格JSON格式。"),
                LLMMessage(role="user", content="\n".join(prompt_parts)),
            ]
        )
        analysis = self.llm._parse_json_response(resp.content)

        # 生成最终信号
        signals: list[Signal] = []
        final_signal = analysis.get("final_signal", "hold")
        symbol = analysis.get("symbol", event.symbol or "UNKNOWN")
        position_pct = analysis.get("position_pct", 0.0)
        confidence = analysis.get("confidence", 0.0)

        if final_signal in ("buy", "sell") and confidence >= 0.5:
            direction = Direction.BUY if final_signal == "buy" else Direction.SELL
            # 仓位百分比转换为股数（简化：假设每1% = 100股）
            quantity = max(100, int(position_pct * 100))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=direction,
                    quantity=quantity,
                    price=None,
                    confidence=confidence,
                    reason=f"[组合决策] {analysis.get('reasoning', '')}",
                    strategy=self.name,
                )
            )

        return SkillResult(
            skill_name=self.name,
            signals=signals,
            analysis=analysis,
            reasoning=analysis.get("reasoning", ""),
            confidence=confidence,
        )
