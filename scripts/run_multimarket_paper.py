"""多市场模拟盘运行脚本 —— A股/港股/美股.

用法:
    python scripts/run_multimarket_paper.py --symbols 300750.SZ 0700.HK AAPL --cycles 5 --interval 30
"""

from __future__ import annotations

import argparse
import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from investment_agent.llm.adapter import LLMAdapter
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.multimarket_sensor import MultiMarketPriceSensor
from investment_agent.simulation.paper_trading import PaperTradingEngine
from investment_agent.skills.mock_skill import MockAgentSkill
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("multimarket_paper")


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Market Paper Trading")
    parser.add_argument("--symbols", nargs="+", default=["300750.SZ", "0700.HK", "AAPL"])
    parser.add_argument("--cash", type=float, default=1_000_000.0)
    parser.add_argument("--interval", type=float, default=30.0, help="Cycle interval (seconds)")
    parser.add_argument("--cycles", type=int, default=5, help="Number of cycles")
    parser.add_argument("--threshold", type=float, default=1.0, help="Price change threshold (%)")
    parser.add_argument("--mock", action="store_true", help="Use MockAgentSkill instead of real LLM")
    args = parser.parse_args()

    llm = LLMAdapter()
    logger.info("LLM: %s @ %s", llm.model, llm.base_url)

    orch = AgentOrchestrator(llm=llm)
    orch.register_sensor(
        MultiMarketPriceSensor(symbols=args.symbols, change_threshold=args.threshold)
    )

    if args.mock:
        orch.register_skill(MockAgentSkill(priority=100))
    else:
        orch.register_skill(NewsAnalysisSkill(llm=llm, priority=100))

    if not args.mock:
        orch.register_advisor(PortfolioAdvisorSkill(llm=llm, priority=50))

    engine = PaperTradingEngine(
        orchestrator=orch,
        initial_cash=args.cash,
        cycle_interval=args.interval,
        symbols=args.symbols,
    )

    logger.info("=" * 50)
    logger.info("🌍 多市场模拟盘启动")
    logger.info("标的: %s", args.symbols)
    logger.info("模式: %s", "Mock" if args.mock else "Real LLM")
    logger.info("阈值: %.1f%%", args.threshold)
    logger.info("=" * 50)

    for i in range(1, args.cycles + 1):
        logger.info("\n--- Cycle %d / %d ---", i, args.cycles)
        report = engine.run_cycle()
        logger.info(
            "[Cycle %d] 净值: %.2f | 现金: %.2f | 持仓: %s | 交易: %d",
            i, report["total_value"], report["cash"],
            report["positions"], report["trade_count"],
        )

    engine.portfolio.export_trades("paper_trades_multimarket.json")
    logger.info("\n交易记录已导出: paper_trades_multimarket.json")

    report = engine.portfolio.report()
    logger.info("\n📊 最终汇总")
    logger.info("净值: %.2f", report["total_value"])
    logger.info("现金: %.2f", report["cash"])
    logger.info("持仓: %s", report["positions"])
    logger.info("交易次数: %d", report["trade_count"])


if __name__ == "__main__":
    main()
