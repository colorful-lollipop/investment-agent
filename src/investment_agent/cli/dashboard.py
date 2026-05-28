"""Rich CLI 实时看板 —— Agent 事件流与信号监控.

用法:
    python -m investment_agent.cli.dashboard --symbols 300750.SZ 600519.SH
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.akshare_sensor import AKShareDataSensor
from investment_agent.sensors.news_sensor import NewsSensor
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill

logger = logging.getLogger("dashboard")


class AgentDashboard:
    """Rich 实时看板."""

    def __init__(self, orchestrator: AgentOrchestrator, refresh_interval: float = 30.0) -> None:
        self.orchestrator = orchestrator
        self.refresh_interval = refresh_interval
        self.console = Console()
        self.events_log: list[dict[str, Any]] = []
        self.signals_log: list[dict[str, Any]] = []
        self._running = False

    def _make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(name="events"),
            Layout(name="signals"),
        )
        return layout

    def _render_header(self) -> Panel:
        text = Text(
            f"🤖 Investment Agent 实时看板  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="bold cyan",
        )
        return Panel(Align.center(text), style="cyan")

    def _render_events(self) -> Panel:
        table = Table(title="最近事件", show_header=True, header_style="bold magenta")
        table.add_column("时间", style="dim", width=16)
        table.add_column("类型", width=10)
        table.add_column("标的", width=12)
        table.add_column("标题", width=30)
        table.add_column("来源", width=10)

        for ev in self.events_log[-10:]:
            table.add_row(
                ev.get("time", "")[11:16],
                ev.get("type", ""),
                ev.get("symbol", "") or "-",
                ev.get("title", "")[:28],
                ev.get("source", "")[:8],
            )
        return Panel(table, border_style="magenta")

    def _render_signals(self) -> Panel:
        table = Table(title="交易信号", show_header=True, header_style="bold green")
        table.add_column("时间", style="dim", width=16)
        table.add_column("标的", width=12)
        table.add_column("方向", width=8)
        table.add_column("数量", justify="right", width=10)
        table.add_column("价格", justify="right", width=10)
        table.add_column("置信度", justify="right", width=8)

        for sig in self.signals_log[-10:]:
            direction_style = "green" if sig.get("direction") == "BUY" else "red"
            table.add_row(
                sig.get("time", "")[11:16],
                sig.get("symbol", ""),
                Text(sig.get("direction", ""), style=direction_style),
                f"{sig.get('quantity', 0):.0f}",
                f"{sig.get('price', 0):.2f}",
                f"{sig.get('confidence', 0):.2f}",
            )
        return Panel(table, border_style="green")

    def _render_footer(self) -> Panel:
        text = Text(
            f"事件总数: {len(self.events_log)}  |  "
            f"信号总数: {len(self.signals_log)}  |  "
            f"刷新间隔: {self.refresh_interval:.0f}s  |  "
            f"按 Ctrl+C 退出",
            style="dim",
        )
        return Panel(Align.center(text))

    def _update(self) -> Layout:
        layout = self._make_layout()
        layout["header"].update(self._render_header())
        layout["events"].update(self._render_events())
        layout["signals"].update(self._render_signals())
        layout["footer"].update(self._render_footer())
        return layout

    def _run_cycle(self) -> None:
        """执行一次 Agent cycle 并记录结果."""
        try:
            signals = self.orchestrator.run_cycle()
            for sig in signals:
                self.signals_log.append(
                    {
                        "time": datetime.now().isoformat(),
                        "symbol": sig.symbol,
                        "direction": sig.direction.value,
                        "quantity": sig.quantity,
                        "price": sig.price,
                        "confidence": sig.confidence,
                        "reason": sig.reason,
                    }
                )
            # 同时记录新事件
            for ev in self.orchestrator._event_history[-5:]:
                self.events_log.append(
                    {
                        "time": ev.timestamp.isoformat(),
                        "type": ev.event_type.value,
                        "symbol": ev.symbol or "",
                        "title": ev.title,
                        "source": ev.source,
                    }
                )
        except Exception as exc:
            logger.warning("Cycle error: %s", exc)

    def run(self) -> None:
        """启动看板循环."""
        self._running = True
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, show_path=False)],
        )

        with Live(self._update(), console=self.console, refresh_per_second=1) as live:
            while self._running:
                self._run_cycle()
                live.update(self._update())
                try:
                    time.sleep(self.refresh_interval)
                except KeyboardInterrupt:
                    self._running = False
                    break

        self.console.print("\n[bold yellow]👋 看板已退出[/bold yellow]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Investment Agent Dashboard")
    parser.add_argument("--symbols", nargs="+", default=["300750.SZ", "600519.SH"])
    parser.add_argument("--interval", type=float, default=30.0, help="刷新间隔(秒)")
    args = parser.parse_args()

    orch = AgentOrchestrator()
    orch.register_sensor(AKShareDataSensor(symbols=args.symbols, limit=3))
    orch.register_sensor(NewsSensor(limit=3))
    orch.register_skill(NewsAnalysisSkill(priority=100))
    orch.register_advisor(PortfolioAdvisorSkill(priority=50))

    dashboard = AgentDashboard(orchestrator=orch, refresh_interval=args.interval)
    dashboard.run()


if __name__ == "__main__":
    main()
