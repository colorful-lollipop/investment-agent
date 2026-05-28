"""新闻分析 Skill —— 使用 LLM 分析新闻事件并生成交易信号."""

from __future__ import annotations

from typing import Any

from investment_agent.core.types import Direction, Signal
from investment_agent.llm.adapter import LLMAdapter
from investment_agent.sensors.base import MarketEvent
from investment_agent.skills.base import Skill, SkillResult


class NewsAnalysisSkill(Skill):
    """新闻情绪分析 Skill.

    使用 LLM 对新闻进行深度分析，输出:
    - 情绪评分 (sentiment_score)
    - 影响级别 (impact_level)
    - 交易信号 (buy/sell/hold/watch)
    - 目标标的和仓位建议
    """

    def __init__(
        self,
        llm: LLMAdapter | None = None,
        sentiment_threshold: float = 0.3,
        name: str = "NewsAnalysisSkill",
    ) -> None:
        super().__init__(name=name, description="Analyze financial news sentiment with LLM")
        self.llm = llm or LLMAdapter()
        self.sentiment_threshold = sentiment_threshold

    def execute(self, event: MarketEvent, context: dict[str, Any] | None = None) -> SkillResult:
        """分析新闻事件."""
        if not event.content:
            return SkillResult(skill_name=self.name, reasoning="Empty event content")

        # 使用 LLM 分析新闻
        analysis = self.llm.analyze_news(
            news_text=event.to_prompt_text(),
            symbol=event.symbol,
        )

        # 从 LLM 分析结果生成交易信号
        signals: list[Signal] = []
        sentiment_score = analysis.get("sentiment_score", 0.0)
        trading_signal = analysis.get("trading_signal", "hold")
        confidence = analysis.get("confidence", 0.0)
        impact_level = analysis.get("impact_level", "low")

        # 仅在高置信度和显著情绪时生成信号
        if confidence >= 0.6 and impact_level in ("high", "medium"):
            signals = self._convert_to_signals(
                trading_signal=trading_signal,
                sentiment_score=sentiment_score,
                symbol=event.symbol or "UNKNOWN",
                confidence=confidence,
                reasoning=analysis.get("summary", ""),
            )

        return SkillResult(
            skill_name=self.name,
            signals=signals,
            analysis=analysis,
            reasoning=analysis.get("summary", ""),
            confidence=confidence,
        )

    def _convert_to_signals(
        self,
        trading_signal: str,
        sentiment_score: float,
        symbol: str,
        confidence: float,
        reasoning: str,
    ) -> list[Signal]:
        """将 LLM 交易信号转换为系统 Signal 对象."""
        signals: list[Signal] = []

        if trading_signal == "buy" and sentiment_score > self.sentiment_threshold:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.BUY,
                    quantity=100,  # 基础仓位，实际应由 Portfolio 管理
                    price=None,
                    confidence=confidence,
                    reason=f"[新闻利好] {reasoning}",
                    strategy=self.name,
                )
            )
        elif trading_signal == "sell" and sentiment_score < -self.sentiment_threshold:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction=Direction.SELL,
                    quantity=100,
                    price=None,
                    confidence=confidence,
                    reason=f"[新闻利空] {reasoning}",
                    strategy=self.name,
                )
            )

        return signals
