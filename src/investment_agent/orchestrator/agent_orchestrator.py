"""AI Agent 编排器 —— 事件驱动的金融感知-分析-决策-执行闭环.

参考 AutoGen 的 ConversableAgent 和 CrewAI 的 Process Manager 设计:
- 异步事件驱动架构
- 多 Skill 并行执行
- LLM 驱动的决策融合
- 与现有量化系统无缝集成
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from investment_agent.core.types import Signal
from investment_agent.execution.risk import RiskManager
from investment_agent.llm.adapter import LLMAdapter
from investment_agent.sensors.base import MarketEvent, Sensor
from investment_agent.skills.base import Skill, SkillResult

logger = logging.getLogger("AgentOrchestrator")


class AgentOrchestrator:
    """AI Agent 编排器.

    工作流程:
    1. 监听传感器事件 (新闻/宏观/价格)
    2. 触发匹配的 Skill 并行分析
    3. Skill 使用 LLM 进行深度推理
    4. PortfolioAdvisorSkill 综合所有分析结果
    5. 输出最终交易信号
    6. 信号进入现有风控/执行系统

    示例:
        >>> orch = AgentOrchestrator(llm=LLMAdapter(model="gpt-4o-mini"))
        >>> orch.register_sensor(NewsSensor())
        >>> orch.register_skill(NewsAnalysisSkill())
        >>> orch.register_skill(MacroAnalysisSkill())
        >>> orch.register_advisor(PortfolioAdvisorSkill())
        >>> signals = orch.run_cycle()
    """

    def __init__(
        self,
        llm: LLMAdapter | None = None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self.llm = llm or LLMAdapter()
        self.risk_manager = risk_manager
        self._sensors: list[Sensor] = []
        self._skills: list[Skill] = []
        self._advisor: Skill | None = None
        self._event_history: list[MarketEvent] = []
        self._max_history = 100

    # ---------- 注册组件 ----------

    def register_sensor(self, sensor: Sensor) -> AgentOrchestrator:
        """注册传感器."""
        self._sensors.append(sensor)
        logger.info("Registered sensor: %s", sensor.name)
        return self

    def register_skill(self, skill: Skill) -> AgentOrchestrator:
        """注册分析 Skill."""
        self._skills.append(skill)
        logger.info("Registered skill: %s", skill.name)
        return self

    def register_advisor(self, advisor: Skill) -> AgentOrchestrator:
        """注册组合顾问 Skill（最终决策层）."""
        self._advisor = advisor
        logger.info("Registered advisor: %s", advisor.name)
        return self

    # ---------- 核心循环 ----------

    def poll_events(self) -> list[MarketEvent]:
        """轮询所有传感器获取新事件."""
        events: list[MarketEvent] = []
        for sensor in self._sensors:
            try:
                new_events = sensor.poll()
                events.extend(new_events)
                logger.debug("Sensor %s polled %d events", sensor.name, len(new_events))
            except Exception:
                logger.exception("Sensor %s failed", sensor.name)
        # 去重并保存历史
        for e in events:
            if e not in self._event_history:
                self._event_history.append(e)
        self._event_history = self._event_history[-self._max_history :]
        return events

    def analyze_event(self, event: MarketEvent) -> list[SkillResult]:
        """用所有启用的 Skill 分析单个事件."""
        results: list[SkillResult] = []
        context: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "event_history": self._event_history,
        }

        for skill in self._skills:
            if not skill.is_enabled():
                continue
            try:
                result = skill.execute(event, context)
                results.append(result)
                logger.info(
                    "Skill %s analyzed event '%s': confidence=%.2f, signals=%d",
                    skill.name,
                    event.title[:40],
                    result.confidence,
                    len(result.signals),
                )
            except Exception:
                logger.exception("Skill %s failed on event '%s'", skill.name, event.title)

        return results

    def synthesize(self, event: MarketEvent, skill_results: list[SkillResult]) -> list[Signal]:
        """综合所有 Skill 结果，生成最终交易信号."""
        if not self._advisor:
            # 没有顾问时，直接合并所有 Skill 的信号
            signals: list[Signal] = []
            for sr in skill_results:
                signals.extend(sr.signals)
            return signals

        context = {"skill_results": skill_results}
        try:
            final_result = self._advisor.execute(event, context)
            logger.info(
                "Advisor %s synthesized: confidence=%.2f, signals=%d",
                self._advisor.name,
                final_result.confidence,
                len(final_result.signals),
            )
            return final_result.signals
        except Exception:
            logger.exception("Advisor failed")
            return []

    def run_cycle(self) -> list[Signal]:
        """运行一个完整的感知-分析-决策周期.

        Returns:
            所有生成的交易信号（已去重）
        """
        all_signals: list[Signal] = []
        events = self.poll_events()
        if not events:
            logger.info("No new events in this cycle")
            return all_signals

        for event in events:
            logger.info("Processing event: [%s] %s", event.event_type.value, event.title)
            skill_results = self.analyze_event(event)
            signals = self.synthesize(event, skill_results)
            all_signals.extend(signals)

        # 简单去重：同标的同方向保留置信度最高的
        all_signals = self._dedup_signals(all_signals)
        logger.info("Cycle complete: %d signals generated", len(all_signals))
        return all_signals

    def run_with_mock(self) -> list[Signal]:
        """使用模拟事件运行完整周期（用于演示和测试）."""
        all_signals: list[Signal] = []

        for sensor in self._sensors:
            if hasattr(sensor, "get_mock_events"):
                mock_events = sensor.get_mock_events()
                for event in mock_events:
                    logger.info("[MOCK] Event: [%s] %s", event.event_type.value, event.title)
                    skill_results = self.analyze_event(event)
                    signals = self.synthesize(event, skill_results)
                    all_signals.extend(signals)

        all_signals = self._dedup_signals(all_signals)
        return all_signals

    @staticmethod
    def _dedup_signals(signals: list[Signal]) -> list[Signal]:
        """信号去重：同标的同方向保留置信度最高的."""
        best: dict[tuple[str, str], Signal] = {}
        for sig in signals:
            key = (sig.symbol, sig.direction.name)
            if key not in best or sig.confidence > best[key].confidence:
                best[key] = sig
        return list(best.values())
