"""真实 LLM 模拟盘运行脚本（小米 mimo-v2.5-pro）.

用法:
    python scripts/run_paper_trading_real.py --symbols 300750.SZ --cycles 2 --interval 30
"""

from __future__ import annotations

import argparse
import logging
import os
import time

from dotenv import load_dotenv

# 显式加载 .env（确保小米 API 配置生效）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from investment_agent.llm.adapter import LLMAdapter
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.akshare_sensor import AKShareDataSensor
from investment_agent.simulation.paper_trading import PaperTradingEngine
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("paper_trading_real")


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper Trading with REAL LLM (Xiaomi)")
    parser.add_argument("--symbols", nargs="+", default=["300750.SZ"])
    parser.add_argument("--cash", type=float, default=1_000_000.0)
    parser.add_argument("--interval", type=float, default=30.0, help="Cycle interval (seconds)")
    parser.add_argument("--cycles", type=int, default=2, help="Number of cycles to run")
    parser.add_argument("--model", default=None, help="Override LLM model")
    args = parser.parse_args()

    # 初始化小米 LLM
    llm = LLMAdapter(model=args.model)
    logger.info("LLM 配置: model=%s, base_url=%s", llm.model, llm.base_url)
    logger.info("API Key 前缀: %s...", llm.api_key[:8])

    orch = AgentOrchestrator(llm=llm)
    # 只获取 1 条新闻，减少 LLM 调用次数
    orch.register_sensor(AKShareDataSensor(symbols=args.symbols, limit=1))
    # 真实 LLM Skill
    orch.register_skill(NewsAnalysisSkill(llm=llm, priority=100))
    # 组合顾问（也走真实 LLM）
    orch.register_advisor(PortfolioAdvisorSkill(llm=llm, priority=50))

    engine = PaperTradingEngine(
        orchestrator=orch,
        initial_cash=args.cash,
        cycle_interval=args.interval,
        symbols=args.symbols,
    )

    logger.info("=" * 50)
    logger.info("🚀 真实 LLM 模拟盘启动")
    logger.info("模型: %s", llm.model)
    logger.info("标的: %s", args.symbols)
    logger.info("初始资金: %.0f", args.cash)
    logger.info("运行周期: %d", args.cycles)
    logger.info("=" * 50)

    # 手动运行指定 cycle 数
    for i in range(1, args.cycles + 1):
        logger.info("\n--- Cycle %d / %d ---", i, args.cycles)
        report = engine.run_cycle()
        logger.info(
            "[Cycle %d] 净值: %.2f | 现金: %.2f | 持仓: %s | 交易: %d",
            i, report["total_value"], report["cash"],
            report["positions"], report["trade_count"],
        )
        if i < args.cycles:
            time.sleep(args.interval)

    # 导出交易记录
    engine.portfolio.export_trades("paper_trades_real.json")
    logger.info("\n交易记录已导出: paper_trades_real.json")

    # 最终汇总
    report = engine.portfolio.report()
    logger.info("\n📊 最终汇总")
    logger.info("净值: %.2f", report["total_value"])
    logger.info("现金: %.2f", report["cash"])
    logger.info("交易次数: %d", report["trade_count"])
    if report["latest_trade"]:
        logger.info("最后一笔: %s %s @ %.2f", report["latest_trade"]["direction"], report["latest_trade"]["symbol"], report["latest_trade"]["price"])


if __name__ == "__main__":
    main()
