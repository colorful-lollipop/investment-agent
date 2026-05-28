"""小米 API 端到端测试 —— 真实 LLM 调用验证."""

import os
from dotenv import load_dotenv

# 显式加载项目根目录的 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from investment_agent.llm.adapter import LLMAdapter, LLMMessage
from investment_agent.sensors.base import EventType, MarketEvent
from investment_agent.sensors.news_sensor import NewsSensor
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator


def test_llm_basic_chat() -> None:
    """测试基础 chat 调用."""
    print("\n=== 1. 基础 LLM Chat 测试 ===")
    llm = LLMAdapter()
    print(f"模型: {llm.model}")
    print(f"base_url: {llm.base_url}")
    print(f"api_key: {llm.api_key[:8]}...")

    resp = llm.chat(
        messages=[
            LLMMessage(role="system", content="你是一个量化金融助手，用简短中文回答。"),
            LLMMessage(role="user", content="请一句话评价宁德时代(300750.SZ)的投资价值。"),
        ]
    )
    print(f"响应内容: {resp.content[:300]}")
    print("✅ 基础 chat 成功")


def test_news_skill() -> None:
    """测试 NewsSkill 端到端."""
    print("\n=== 2. NewsAnalysisSkill 端到端测试 ===")
    llm = LLMAdapter()
    skill = NewsAnalysisSkill(llm=llm)

    event = MarketEvent(
        event_type=EventType.NEWS,
        title="宁德时代发布新一代固态电池技术",
        content="宁德时代宣布其最新固态电池能量密度突破500Wh/kg，预计2026年量产。该技术将大幅提升电动车续航里程。",
        symbol="300750.SZ",
        source="模拟新闻",
    )

    result = skill.execute(event, context=None)
    print(f"Skill 返回信号数: {len(result.signals)}")
    if result.signals:
        sig = result.signals[0]
        print(f"  方向: {sig.direction.value}, 置信度: {sig.confidence:.2f}")
        print(f"  理由: {sig.reason[:200]}")
    print(f"推理: {result.reasoning[:200]}")
    print("✅ NewsSkill 成功")


def test_orchestrator_e2e() -> None:
    """测试编排器端到端."""
    print("\n=== 3. Orchestrator 端到端测试 ===")
    orch = AgentOrchestrator()
    orch.register_sensor(NewsSensor())
    orch.register_skill(NewsAnalysisSkill(priority=100))
    orch.register_skill(PortfolioAdvisorSkill(priority=50))

    signals = orch.run_cycle()
    print(f"生成信号数: {len(signals)}")
    for s in signals:
        print(f"  {s.symbol}: {s.direction.value} qty={s.quantity} conf={s.confidence:.2f}")
    print("✅ Orchestrator 成功")


if __name__ == "__main__":
    test_llm_basic_chat()
    test_news_skill()
    test_orchestrator_e2e()
    print("\n🎉 所有端到端测试完成")
