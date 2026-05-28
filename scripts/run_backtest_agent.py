"""Agent 策略历史回测验证.

用法:
    python scripts/run_backtest_agent.py --symbols 000001.SZ 600519.SH --days 180
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta

from investment_agent.backtest.engine import BacktestEngine
from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.execution.risk import RiskManager
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.skills.mock_skill import MockAgentSkill
# from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill
from investment_agent.strategy.agent_strategy import AgentStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backtest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Strategy Backtest")
    parser.add_argument("--symbols", nargs="+", default=["000001.SZ", "600519.SH"])
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--cash", type=float, default=1_000_000.0)
    parser.add_argument("--threshold", type=float, default=2.0, help="价格变动阈值(%)")
    args = parser.parse_args()

    end = datetime(2024, 12, 31)
    start = end - timedelta(days=args.days)

    # 1. 数据
    provider = MockDataProvider(seed=42, trend=0.0002, volatility=0.025)

    # 2. Agent 编排器（使用 Mock Skill，不调用 LLM，回测速度快）
    orch = AgentOrchestrator()
    orch.register_skill(MockAgentSkill(priority=100))
    # orch.register_advisor(PortfolioAdvisorSkill(priority=50))

    # 3. Agent 策略
    agent_strat = AgentStrategy(
        orchestrator=orch,
        price_change_threshold=args.threshold,
        name="AgentBacktest",
    )

    # 4. 回测引擎
    engine = BacktestEngine(
        data_provider=provider,
        strategies=[agent_strat],
        risk_manager=RiskManager(config={"max_position_pct": 0.3, "stop_loss_pct": 0.05}),
        initial_cash=args.cash,
    )

    logger.info("=" * 50)
    logger.info("开始 Agent 策略回测")
    logger.info("标的: %s", args.symbols)
    logger.info("区间: %s ~ %s", start.date(), end.date())
    logger.info("初始资金: %.0f", args.cash)
    logger.info("=" * 50)

    metrics = engine.run(symbols=args.symbols, start=start, end=end)

    logger.info("\n%s", metrics)
    logger.info("\n最终净值: %.2f", engine.account.total_value)
    logger.info("最终现金: %.2f", engine.account.cash)
    logger.info("持仓明细:")
    for sym, pos in engine.account.positions.items():
        if pos.quantity > 0:
            logger.info("  %s: %.0f 股, 成本 %.2f", sym, pos.quantity, pos.avg_cost)


if __name__ == "__main__":
    main()
