"""模拟盘引擎 —— 虚拟持仓与盈亏跟踪.

设计要点:
- 不连接真实交易所，所有订单在本地模拟成交
- 定时轮询 Sensor → Agent 分析 → 生成信号 → 虚拟下单 → 更新持仓
- 支持接入真实行情数据（AKShare）更新持仓市值
- 记录完整交易日志，可导出为 CSV/JSON

用法:
    python scripts/run_paper_trading.py --symbols 300750.SZ 600519.SH --duration 300
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_agent.core.types import Direction, Fill, Signal
from investment_agent.execution.broker import MockBroker
from investment_agent.execution.risk import RiskManager
from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger("paper_trading")


@dataclass
class TradeRecord:
    """交易记录."""

    timestamp: datetime
    symbol: str
    direction: str
    quantity: float
    price: float
    amount: float
    commission: float
    signal_reason: str = ""


@dataclass
class PaperPortfolio:
    """模拟盘组合状态."""

    cash: float = 1_000_000.0
    positions: dict[str, dict[str, Any]] = field(default_factory=dict)
    trade_history: list[TradeRecord] = field(default_factory=list)
    total_value_history: list[tuple[datetime, float]] = field(default_factory=list)

    def update_position(self, fill: Fill) -> None:
        """根据成交回报更新持仓."""
        sym = fill.symbol
        qty = fill.quantity
        cost = fill.price * qty
        commission = fill.price * qty * 0.0003  # 佣金

        if fill.direction == Direction.BUY:
            self.cash -= cost + commission
            if sym not in self.positions:
                self.positions[sym] = {"quantity": 0.0, "avg_cost": 0.0, "total_cost": 0.0}
            pos = self.positions[sym]
            new_qty = pos["quantity"] + qty
            pos["total_cost"] = pos["total_cost"] + cost
            pos["avg_cost"] = pos["total_cost"] / new_qty if new_qty > 0 else 0.0
            pos["quantity"] = new_qty
        else:
            self.cash += cost - commission
            if sym in self.positions:
                self.positions[sym]["quantity"] -= qty
                if self.positions[sym]["quantity"] <= 0:
                    self.positions[sym]["quantity"] = 0.0

        self.trade_history.append(
            TradeRecord(
                timestamp=fill.timestamp,
                symbol=sym,
                direction=fill.direction.name,
                quantity=qty,
                price=fill.price,
                amount=cost,
                commission=commission,
            )
        )

    def update_market_prices(self, prices: dict[str, float]) -> None:
        """更新持仓市值并记录净值."""
        market_value = 0.0
        for sym, pos in self.positions.items():
            if pos["quantity"] > 0 and sym in prices:
                market_value += pos["quantity"] * prices[sym]
        total = self.cash + market_value
        self.total_value_history.append((datetime.now(), total))

    @property
    def total_value(self) -> float:
        if not self.total_value_history:
            return self.cash
        return self.total_value_history[-1][1]

    def report(self) -> dict[str, Any]:
        return {
            "cash": round(self.cash, 2),
            "total_value": round(self.total_value, 2),
            "positions": {
                sym: {"qty": round(p["quantity"], 2), "avg_cost": round(p["avg_cost"], 2)}
                for sym, p in self.positions.items()
                if p["quantity"] > 0
            },
            "trade_count": len(self.trade_history),
            "latest_trade": (
                {
                    "symbol": self.trade_history[-1].symbol,
                    "direction": self.trade_history[-1].direction,
                    "price": self.trade_history[-1].price,
                }
                if self.trade_history
                else None
            ),
        }

    def export_trades(self, path: str) -> None:
        """导出交易记录为 JSON."""
        data = [
            {
                "timestamp": r.timestamp.isoformat(),
                "symbol": r.symbol,
                "direction": r.direction,
                "quantity": r.quantity,
                "price": r.price,
                "amount": r.amount,
                "commission": r.commission,
            }
            for r in self.trade_history
        ]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class PaperTradingEngine:
    """模拟盘引擎."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        risk_manager: RiskManager | None = None,
        initial_cash: float = 1_000_000.0,
        cycle_interval: float = 30.0,
        symbols: list[str] | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.risk_manager = risk_manager or RiskManager()
        self.portfolio = PaperPortfolio(cash=initial_cash)
        self.broker = MockBroker()
        self.cycle_interval = cycle_interval
        self.symbols = symbols or ["300750.SZ", "600519.SH"]
        self._running = False

    def _get_current_prices(self) -> dict[str, float]:
        """获取当前价格（优先 AKShare，失败用 mock）."""
        prices: dict[str, float] = {}
        try:
            import akshare as ak

            for sym in self.symbols:
                code = sym.split(".")[0]
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    row = df[df["代码"] == code]
                    if not row.empty:
                        prices[sym] = float(row.iloc[0]["最新价"])
        except Exception:
            # fallback: 随机价格
            import random

            for sym in self.symbols:
                prices[sym] = random.uniform(50, 200)
        return prices

    def _execute_signals(self, signals: list[Signal]) -> None:
        """执行信号并更新持仓."""
        from investment_agent.core.types import Account, Position

        prices = self._get_current_prices()
        # 构建 Account 供 RiskManager 使用
        account = Account(cash=self.portfolio.cash)
        for sym, pos in self.portfolio.positions.items():
            p = Position(symbol=sym, quantity=pos["quantity"], avg_cost=pos["avg_cost"])
            if sym in prices:
                p.update_market_price(prices[sym])
            account.positions[sym] = p

        for sig in signals:
            order = self.risk_manager.evaluate(sig, account, prices)
            if order:
                self.broker.send_order(order)
        fills = self.broker.get_fills()
        for fill in fills:
            self.portfolio.update_position(fill)
        self.portfolio.update_market_prices(prices)

    def run_cycle(self) -> dict[str, Any]:
        """运行一个交易周期."""
        signals = self.orchestrator.run_cycle()
        self._execute_signals(signals)
        return self.portfolio.report()

    def run(self, duration_seconds: float | None = None) -> None:
        """启动模拟盘循环.

        Args:
            duration_seconds: 运行时长（秒），None 表示无限循环
        """
        self._running = True
        start_time = time.time()
        cycle_count = 0

        logger.info("=" * 50)
        logger.info("模拟盘启动")
        logger.info("标的: %s", self.symbols)
        logger.info("初始资金: %.0f", self.portfolio.cash)
        logger.info("周期间隔: %.0fs", self.cycle_interval)
        logger.info("=" * 50)

        try:
            while self._running:
                cycle_count += 1
                report = self.run_cycle()
                logger.info(
                    "[Cycle %d] 净值: %.2f | 现金: %.2f | 持仓: %s | 交易: %d",
                    cycle_count,
                    report["total_value"],
                    report["cash"],
                    report["positions"],
                    report["trade_count"],
                )

                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info("达到运行时长限制，停止模拟盘")
                    break

                time.sleep(self.cycle_interval)
        except KeyboardInterrupt:
            logger.info("用户中断模拟盘")
        finally:
            self._running = False
            self._print_summary()

    def _print_summary(self) -> None:
        """打印最终汇总."""
        logger.info("\n%s", "=" * 50)
        logger.info("模拟盘结束汇总")
        logger.info("=" * 50)
        report = self.portfolio.report()
        logger.info("最终净值: %.2f", report["total_value"])
        logger.info("最终现金: %.2f", report["cash"])
        logger.info("总交易次数: %d", report["trade_count"])
        logger.info("当前持仓:")
        for sym, pos in report["positions"].items():
            logger.info("  %s: %s", sym, pos)
