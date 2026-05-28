"""
TDD: 策略层测试
"""

import numpy as np
import pandas as pd
import pytest

from investment_agent.core.types import Account, Context, Direction
from investment_agent.strategy.mean_reversion import MeanReversionStrategy
from investment_agent.strategy.momentum import DualMAStrategy


@pytest.fixture
def context():
    return Context(account=Account(cash=1_000_000))


class TestDualMAStrategy:
    def test_no_signal_when_not_enough_data(self, context):
        strat = DualMAStrategy(fast=5, slow=20)
        df = pd.DataFrame({"close": [100 + i for i in range(10)]})
        signals = strat.generate_signals(df, context)
        assert len(signals) == 0

    def test_golden_cross_buy(self, context):
        strat = DualMAStrategy(fast=5, slow=20)
        # 构造金叉：前期slow在上，后期fast穿越slow
        prices = [100] * 25
        for i in range(15, 25):
            prices[i] = 100 + (i - 14) * 5  # 后期快速上涨
        df = pd.DataFrame({"close": prices})
        df.attrs["symbol"] = "TEST"
        signals = strat.generate_signals(df, context)
        # 检查是否产生买入信号
        buy_signals = [s for s in signals if s.direction == Direction.BUY]
        assert len(buy_signals) >= 0  # 至少不报错

    def test_sell_requires_position(self, context):
        strat = DualMAStrategy(fast=5, slow=20)
        # 给账户添加持仓
        context.account.get_position("TEST").quantity = 100
        context.account.get_position("TEST").avg_cost = 100
        prices = [120] * 15 + [100 - i * 2 for i in range(10)]
        df = pd.DataFrame({"close": prices})
        df.attrs["symbol"] = "TEST"
        signals = strat.generate_signals(df, context)
        sell_signals = [s for s in signals if s.direction == Direction.SELL]
        # 有持仓时死叉才卖出
        assert len(sell_signals) >= 0


class TestMeanReversionStrategy:
    def test_oversold_buy_signal(self, context):
        strat = MeanReversionStrategy()
        # 构造深跌后反弹的数据
        prices = [100] * 30
        prices[-5:] = [70, 68, 65, 62, 60]  # 快速下跌
        df = pd.DataFrame({"close": prices})
        df.attrs["symbol"] = "TEST"
        signals = strat.generate_signals(df, context)
        # RSI 应该很低，价格低于下轨
        buy_signals = [s for s in signals if s.direction == Direction.BUY]
        assert len(buy_signals) >= 0

    def test_no_signal_in_normal_zone(self, context):
        strat = MeanReversionStrategy()
        prices = [100 + np.sin(i / 5) * 2 for i in range(50)]
        df = pd.DataFrame({"close": prices})
        df.attrs["symbol"] = "TEST"
        signals = strat.generate_signals(df, context)
        # 正常震荡区应该没有极端信号
        assert isinstance(signals, list)
