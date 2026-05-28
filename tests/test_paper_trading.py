"""PaperTradingEngine 测试."""

from datetime import datetime

from investment_agent.core.types import Direction, Fill
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.simulation.paper_trading import PaperPortfolio, PaperTradingEngine


class TestPaperPortfolio:
    def test_buy_updates_position(self) -> None:
        pf = PaperPortfolio(cash=100000)
        fill = Fill(
            order_id="test1",
            symbol="000001.SZ",
            direction=Direction.BUY,
            quantity=100,
            price=10.0,
            timestamp=datetime.now(),
        )
        pf.update_position(fill)
        assert pf.positions["000001.SZ"]["quantity"] == 100
        assert pf.cash < 100000
        assert len(pf.trade_history) == 1

    def test_sell_reduces_position(self) -> None:
        pf = PaperPortfolio(cash=100000)
        pf.update_position(
            Fill(
                order_id="test2",
                symbol="000001.SZ",
                direction=Direction.BUY,
                quantity=100,
                price=10.0,
                timestamp=datetime.now(),
            )
        )
        pf.update_position(
            Fill(
                order_id="test3",
                symbol="000001.SZ",
                direction=Direction.SELL,
                quantity=50,
                price=11.0,
                timestamp=datetime.now(),
            )
        )
        assert pf.positions["000001.SZ"]["quantity"] == 50
        assert len(pf.trade_history) == 2

    def test_report(self) -> None:
        pf = PaperPortfolio(cash=90000)
        pf.positions["000001.SZ"] = {"quantity": 100, "avg_cost": 10.0}
        pf.total_value_history.append((datetime.now(), 100000))
        report = pf.report()
        assert report["cash"] == 90000
        assert report["total_value"] == 100000
        assert "000001.SZ" in report["positions"]


class TestPaperTradingEngine:
    def test_init(self) -> None:
        orch = AgentOrchestrator()
        engine = PaperTradingEngine(orchestrator=orch, initial_cash=500000)
        assert engine.portfolio.cash == 500000
        assert engine.cycle_interval == 30.0

    def test_run_cycle_no_signals(self) -> None:
        orch = AgentOrchestrator()
        engine = PaperTradingEngine(orchestrator=orch)
        report = engine.run_cycle()
        assert report["total_value"] == 1_000_000.0
        assert report["trade_count"] == 0
