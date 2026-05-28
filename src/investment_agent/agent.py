"""投资分析Agent主控 —— 系统的调度中枢
支持：回测模式 / 模拟交易模式 / 实盘模式（预留）
"""

import logging
from datetime import datetime

import yaml

from investment_agent.backtest.engine import BacktestEngine
from investment_agent.backtest.metrics import PerformanceMetrics
from investment_agent.core.types import Account, Context, Signal
from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.data.provider import DataProvider
from investment_agent.execution.broker import Broker, MockBroker
from investment_agent.execution.risk import RiskManager
from investment_agent.strategy.base import BaseStrategy
from investment_agent.strategy.mean_reversion import MeanReversionStrategy
from investment_agent.strategy.momentum import DualMAStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InvestmentAgent")


class InvestmentAgent:
    """投资分析Agent
    使用方法：
        agent = InvestmentAgent.from_config("config/config.yaml")
        metrics = agent.backtest(symbols=["000001.SZ"], days=180)
    """

    def __init__(
        self,
        data_provider: DataProvider,
        strategies: list[BaseStrategy],
        risk_manager: RiskManager,
        broker: Broker | None = None,
        initial_cash: float = 1_000_000.0,
    ):
        self.data_provider = data_provider
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.broker = broker or MockBroker()
        self.account = Account(cash=initial_cash)
        self.context = Context(account=self.account)
        logger.info("InvestmentAgent initialized with %d strategies", len(strategies))

    @classmethod
    def from_config(cls, path: str) -> "InvestmentAgent":
        """从 YAML 配置加载 Agent"""
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # 数据源
        dp = MockDataProvider(**cfg.get("data", {}))

        # 策略
        strategies: list[BaseStrategy] = []
        for s_cfg in cfg.get("strategies", []):
            name = s_cfg.pop("name")
            if name == "DualMA":
                strategies.append(DualMAStrategy(**s_cfg))
            elif name == "MeanReversion":
                strategies.append(MeanReversionStrategy(**s_cfg))
            else:
                logger.warning("Unknown strategy: %s", name)

        # 风控
        rm = RiskManager(config=cfg.get("risk", {}))

        return cls(
            data_provider=dp,
            strategies=strategies,
            risk_manager=rm,
            initial_cash=cfg.get("capital", {}).get("initial", 1_000_000),
        )

    def backtest(
        self,
        symbols: list[str],
        days: int = 180,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> PerformanceMetrics:
        """运行回测"""
        engine = BacktestEngine(
            data_provider=self.data_provider,
            strategies=self.strategies,
            risk_manager=self.risk_manager,
            initial_cash=self.account.cash,
        )
        metrics = engine.run(symbols=symbols, start=start, end=end)
        self.account = engine.account  # 同步账户状态
        logger.info(
            "Backtest completed. Annual return: %.2f%%, Max DD: %.2f%%",
            metrics.annual_return * 100,
            metrics.max_drawdown * 100,
        )
        return metrics

    def analyze(self, symbol: str) -> dict:
        """分析单个标的：返回技术面分析摘要"""
        df = self.data_provider.get_daily_bars(symbol, limit=60)
        if df.empty:
            return {"error": f"No data for {symbol}"}

        close = df["close"]
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]

        # 简单趋势判断
        trend = (
            "UP"
            if close.iloc[-1] > ma20 > ma60
            else "DOWN"
            if close.iloc[-1] < ma20 < ma60
            else "SIDEWAY"
        )

        # 波动率
        vol = close.pct_change().std() * (252**0.5)

        return {
            "symbol": symbol,
            "current_price": close.iloc[-1],
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "trend": trend,
            "annual_volatility": vol,
            "data_points": len(df),
        }

    def run_daily(self, symbols: list[str]) -> dict:
        """每日运行：获取数据 → 策略信号 → 风控 → 下单
        （模拟/实盘模式入口）
        """
        self.context.current_time = datetime.now()
        current_prices = {}

        # 更新价格
        for sym in symbols:
            price = self.data_provider.get_current_price(sym)
            if price:
                current_prices[sym] = price
                pos = self.account.get_position(sym)
                if pos.quantity > 0:
                    pos.update_market_price(price)

        # 策略信号
        all_signals: list[Signal] = []
        for strat in self.strategies:
            for sym in symbols:
                df = self.data_provider.get_daily_bars(sym, limit=60)
                df.attrs["symbol"] = sym
                if len(df) >= 20:
                    signals = strat.generate_signals(df, self.context)
                    all_signals.extend(signals)

        # 风控 + 执行
        if isinstance(self.broker, MockBroker):
            self.broker.set_price_source(lambda s, prices=current_prices: prices.get(s))

        executed = 0
        for sig in all_signals:
            order = self.risk_manager.evaluate(sig, self.account, current_prices)
            if order and self.broker:
                self.broker.send_order(order)
                executed += 1

        # 处理成交
        if self.broker:
            fills = self.broker.get_fills()
            for fill in fills:
                self.account.apply_fill(fill)

        logger.info("Daily run completed. Signals: %d, Executed: %d", len(all_signals), executed)
        return {
            "signals": len(all_signals),
            "executed": executed,
            "fills": fills,
            "total_value": self.account.total_value,
        }
