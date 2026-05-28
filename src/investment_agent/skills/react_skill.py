"""ReAct 反射 Skill —— 自我纠错与多步推理.

参考 ReAct (Reasoning + Acting) 范式:
1. Thought: 分析当前事件与上下文
2. Action: 调用底层 Skill 执行分析
3. Observation: 观察执行结果
4. Reflection: 反思结果是否合理，是否需要修正
5. 若 confidence < threshold，则重新执行（最多 max_iterations 次）

与 RAGMemory 结合: 检索相似历史事件作为 Thought 的参考.
"""

from __future__ import annotations

from typing import Any

from investment_agent.llm.adapter import LLMAdapter, LLMMessage
from investment_agent.memory.rag_memory import RAGMemory
from investment_agent.sensors.base import MarketEvent
from investment_agent.skills.base import Skill, SkillResult


class ReActSkill(Skill):
    """ReAct 反射 Skill 包装器.

    包装一个底层 Skill，在执行后自动进行反思和纠错.
    """

    def __init__(
        self,
        inner_skill: Skill,
        llm: LLMAdapter | None = None,
        memory: RAGMemory | None = None,
        confidence_threshold: float = 0.6,
        max_iterations: int = 2,
        priority: int = 0,
    ) -> None:
        super().__init__(
            name=f"ReAct({inner_skill.name})",
            description="ReAct reflection wrapper",
            priority=priority,
        )
        self.inner_skill = inner_skill
        self.llm = llm or LLMAdapter()
        self.memory = memory
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations

    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        """ReAct 循环执行."""
        # Step 1: Thought —— 检索相似历史事件增强上下文
        thought = self._think(event, context)

        best_result: SkillResult | None = None
        for iteration in range(1, self.max_iterations + 1):
            # Step 2: Action —— 调用底层 Skill
            enriched_context = self._build_context(context, thought, iteration)
            result = self.inner_skill.execute(event, enriched_context)

            # Step 3: Observation
            observation = self._observe(result)

            # Step 4: Reflection
            reflection = self._reflect(event, result, thought, observation)

            if best_result is None or result.confidence > best_result.confidence:
                best_result = result

            # 如果 confidence 达标或反思认为合理，提前退出
            if result.confidence >= self.confidence_threshold or reflection.get("satisfied", False):
                break

            # 否则用 reflection 的建议修正 thought，进入下一轮
            thought = reflection.get("improved_thought", thought)

        return best_result or SkillResult(
            skill_name=self.name,
            reasoning="ReAct failed to produce any result",
        )

    def _think(self, event: MarketEvent, context: dict[str, Any] | None) -> str:
        """检索历史相似事件，形成初始思考."""
        parts: list[str] = []
        parts.append(f"当前事件: {event.title}")
        parts.append(f"事件内容: {event.content[:300]}")

        if self.memory:
            similar = self.memory.search(event, n_results=3)
            if similar:
                parts.append("\n历史相似事件参考:")
                for hit in similar:
                    meta = hit.get("metadata", {})
                    parts.append(
                        f"- [{meta.get('event_type', '?')}] {meta.get('title', '')} "
                        f"(相似度距离: {hit.get('distance', 1):.3f})"
                    )

        return "\n".join(parts)

    def _build_context(
        self, context: dict[str, Any] | None, thought: str, iteration: int
    ) -> dict[str, Any]:
        """构建 enriched context."""
        ctx = dict(context) if context else {}
        ctx["react_thought"] = thought
        ctx["react_iteration"] = iteration
        return ctx

    def _observe(self, result: SkillResult) -> str:
        """观察结果摘要."""
        parts = [
            f"Skill: {result.skill_name}",
            f"Confidence: {result.confidence:.2f}",
            f"Signals: {len(result.signals)}",
            f"Reasoning: {result.reasoning[:300]}",
        ]
        return "\n".join(parts)

    def _reflect(
        self,
        event: MarketEvent,
        result: SkillResult,
        thought: str,
        observation: str,
    ) -> dict[str, Any]:
        """用 LLM 反思结果质量."""
        prompt = (
            f"你是一位量化投资审核员。请审核以下分析结果的质量。\n\n"
            f"[原始事件]\n{event.to_prompt_text()}\n\n"
            f"[分析思路]\n{thought[:500]}\n\n"
            f"[分析结果]\n{observation}\n\n"
            f"请输出 JSON:\n"
            f"{{\n"
            f'  "satisfied": true/false,\n'
            f'  "score": 0-1,  // 质量评分\n'
            f'  "issues": "发现的问题",\n'
            f'  "improved_thought": "改进后的分析思路"\n'
            f"}}"
        )

        try:
            resp = self.llm.chat(
                messages=[
                    LLMMessage(
                        role="system",
                        content="你是严格的量化投资审核员，只输出 JSON。",
                    ),
                    LLMMessage(role="user", content=prompt),
                ]
            )
            data = LLMAdapter._parse_json_response(resp.content)
            return {
                "satisfied": data.get("satisfied", result.confidence >= self.confidence_threshold),
                "score": float(data.get("score", result.confidence)),
                "issues": data.get("issues", ""),
                "improved_thought": data.get("improved_thought", thought),
            }
        except Exception:
            # LLM 不可用或解析失败时，用简单规则判断
            return {
                "satisfied": result.confidence >= self.confidence_threshold,
                "score": result.confidence,
                "issues": "",
                "improved_thought": thought,
            }
