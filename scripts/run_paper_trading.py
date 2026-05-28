"""模拟盘运行脚本.

用法:
    python scripts/run_paper_trading.py --symbols 300750.SZ 600519.SH --duration 60
"""

from __future__ import annotations

import argparse
import logging

from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.akshare_sensor import AKShareDataSensor
from investment_agent.sensors.news_sensor import NewsSensor
from investment_agent.simulation.paper_trading import PaperTradingEngine
from investment_agent.skills.mock_skill import MockAgentSkill

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper Trading Simulation")
    parser.add_argument("--symbols", nargs="+", default=["300750.SZ", "600519.SH"])
    parser.add_argument("--cash", type=float, default=1_000_000.0)
    parser.add_argument("--interval", type=float, default=10.0, help="Cycle interval (seconds)")
    parser.add_argument("--duration", type=float, default=60.0, help="Total runtime (seconds)")
    args = parser.parse_args()

    orch = AgentOrchestrator()
    orch.register_sensor(AKShareDataSensor(symbols=args.symbols, limit=2))
    orch.register_sensor(NewsSensor(limit=2))
    orch.register_skill(MockAgentSkill(priority=100))

    engine = PaperTradingEngine(
        orchestrator=orch,
        initial_cash=args.cash,
        cycle_interval=args.interval,
        symbols=args.symbols,
    )

    engine.run(duration_seconds=args.duration)

    # 导出交易记录
    engine.portfolio.export_trades("paper_trades.json")
    print("\n交易记录已导出: paper_trades.json")


if __name__ == "__main__":
    main()
