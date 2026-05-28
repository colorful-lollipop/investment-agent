"""
TDD: ML预测层测试
"""

from investment_agent.data.mock_provider import MockDataProvider
from investment_agent.ml.features import FeatureEngineer
from investment_agent.ml.predictor import XGBLSTMFusionPredictor


class TestFeatureEngineer:
    def test_compute_all(self):
        dp = MockDataProvider(seed=42)
        df = dp.get_daily_bars("A", limit=100)
        feat = FeatureEngineer.compute_all(df)
        assert not feat.empty
        assert "target_5d" in feat.columns
        assert "rsi_14" in feat.columns
        assert "macd" in feat.columns

    def test_rsi_range(self):
        dp = MockDataProvider(seed=42)
        df = dp.get_daily_bars("A", limit=100)
        rsi = FeatureEngineer._rsi(df["close"], 14)
        assert rsi.min() >= 0
        assert rsi.max() <= 100


class TestXGBLSTMFusionPredictor:
    def test_fit_and_predict(self):
        dp = MockDataProvider(seed=42, trend=0.0003, volatility=0.02)
        df = dp.get_daily_bars("A", limit=200)
        model = XGBLSTMFusionPredictor(seq_len=10)
        model.fit(df)
        pred = model.predict(df)
        assert isinstance(pred, float)

    def test_feature_importance(self):
        dp = MockDataProvider(seed=42)
        df = dp.get_daily_bars("A", limit=200)
        model = XGBLSTMFusionPredictor(seq_len=10)
        model.fit(df)
        imp = model.feature_importance()
        assert imp is not None
        assert len(imp) > 0
        assert imp.sum() > 0
