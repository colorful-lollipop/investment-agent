"""事件驱动回测引擎 —— 参考 Backtrader / Zipline 设计
逐 K 线推进，模拟真实交易流程
"""

from datetime import datetime

from investment_agent.backtest.metrics import PerformanceMetrics
from investment_agent.core.types import Account, Context, Portfolio, Signal
from investment_agent.data.provider import DataProvider
from investment_agent.execution.broker import MockBroker
from investment_agent.execution.risk import RiskManager
from investment_agent.strategy.base import BaseStrategy


class BacktestEngine:
    """事件驱动回测引擎
    工作流：
      1. 加载历史数据
      2. 逐 bar 推进
      3. 每个 bar：更新价格 → 策略生成信号 → 风控审核 → Broker 撮合 → 更新账户
      4. 计算绩效
    """

    def __init__(
        self,
        data_provider: DataProvider,
        strategies: list[BaseStrategy],
        risk_manager: RiskManager,
        initial_cash: float = 1_000_000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001,
    ):
        self.data_provider = data_provider
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.account = Account(cash=initial_cash)
        self.broker = MockBroker(
            commission_rate=commission_rate,
            slippage=slippage,
        )
        self.portfolio = Portfolio(account=self.account)
        self.context = Context(account=self.account)

    def run(
        self,
        symbols: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
        warmup_days: int = 60,
    ) -> PerformanceMetrics:
        """运行回测"""
        # 1. 预热数据
        all_data = {}
        for sym in symbols:
            df = self.data_provider.get_daily_bars(
                sym, start=start, end=end, limit=warmup_days + 500
            )
            if df is not None and not df.empty:
                df.attrs["symbol"] = sym
                all_data[sym] = df

        if not all_data:
            raise ValueError("No data loaded for backtest")

        # 2. 找到统一的时间轴（取所有标的的交易日交集）
        common_dates: set | None = None
        for _sym, df in all_data.items():
            dates = set(df.index)
            common_dates = dates if common_dates is None else common_dates.intersection(dates)
        sorted_dates = sorted(common_dates) if common_dates else []

        # 3. 初始化策略
        for strat in self.strategies:
            strat.initialize(self.context)

        # 4. 逐日推进
        for _i, date in enumerate(sorted_dates):
            self.context.current_time = date

            # 更新账户净值快照
            self.account.record_snapshot(date)

            # 更新当前价格 & 持仓市值
            current_prices = {}
            for _sym, df in all_data.items():
                if date in df.index:
                    price = float(df.loc[date, "close"])
                    current_prices[sym] = price
                    pos = self.account.get_position(sym)
                    if pos.quantity > 0:
                        pos.update_market_price(price)

            self.portfolio.current_prices = current_prices
            self.broker.set_price_source(lambda s, prices=current_prices: prices.get(s))

            # 策略生成信号
            all_signals: list[Signal] = []
            for strat in self.strategies:
                for _sym, df in all_data.items():
                    # 截断到当前日期的数据
                    hist = df.loc[:date]
                    if len(hist) >= 20:
                        signals = strat.generate_signals(hist, self.context)
                        all_signals.extend(signals)

            # 风控审核 + 下单
            for sig in all_signals:
                order = self.risk_manager.evaluate(sig, self.account, current_prices)
                if order:
                    self.broker.send_order(order)

            # 处理成交回报
            fills = self.broker.get_fills()
            for fill in fills:
                self.account.apply_fill(fill)
                for strat in self.strategies:
                    strat.on_fill(fill, self.context)

        # 5. 最终快照
        self.account.record_snapshot(sorted_dates[-1])

        # 6. 计算绩效
        return PerformanceMetrics(self.account.total_value_history)
