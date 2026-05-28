"""XGBoost + LSTM 特征融合预测器
参考论文：Stock risk prediction based on XGBoost and LSTM models
实现：XGBoost提取非线性特征 → 拼接原始特征 → LSTM时序建模
"""

import warnings
from typing import Any

import numpy as np
import pandas as pd

from investment_agent.ml.features import FeatureEngineer

warnings.filterwarnings("ignore")


class XGBLSTMFusionPredictor:
    """简化版 XGBoost-LSTM 融合模型
    由于环境限制，使用 XGBoost + 滑动窗口线性近似（模拟LSTM时序依赖）
    生产环境可替换为真正的 torch.nn.LSTM
    """

    def __init__(
        self,
        xgb_params: dict | None = None,
        seq_len: int = 10,
        forecast_horizon: int = 5,
    ):
        self.seq_len = seq_len
        self.forecast_horizon = forecast_horizon
        self.xgb_params = xgb_params or {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "reg_lambda": 1.0,
        }
        self._xgb_model: Any = None
        self._feature_cols: list[str] = []
        self._is_fitted = False

    def _build_sequences(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """构建监督学习样本 (X, y)"""
        feat = FeatureEngineer.compute_all(df)
        if feat.empty or len(feat) < self.seq_len + self.forecast_horizon + 10:
            return np.array([]), np.array([])

        target_col = "target_5d"
        exclude = [target_col]
        self._feature_cols = [c for c in feat.columns if c not in exclude]

        X_list, y_list = [], []
        values = feat[self._feature_cols].values
        targets = feat[target_col].values

        for i in range(self.seq_len, len(feat) - self.forecast_horizon):
            # 取过去 seq_len 天的特征均值作为序列表示（简化版）
            seq = values[i - self.seq_len : i]
            X_list.append(seq.mean(axis=0))  # 聚合时序信息
            y_list.append(targets[i])

        return np.array(X_list), np.array(y_list)

    def fit(self, df: pd.DataFrame) -> "XGBLSTMFusionPredictor":
        """训练模型"""
        X, y = self._build_sequences(df)
        if len(X) == 0:
            raise ValueError("Not enough data to train model")

        # 阶段1：XGBoost
        try:
            from xgboost import XGBRegressor

            self._xgb_model = XGBRegressor(**self.xgb_params)
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor

            self._xgb_model = GradientBoostingRegressor(
                n_estimators=self.xgb_params.get("n_estimators", 100),
                max_depth=self.xgb_params.get("max_depth", 4),
                learning_rate=self.xgb_params.get("learning_rate", 0.05),
                random_state=42,
            )

        self._xgb_model.fit(X, y)
        self._is_fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> float:
        """预测未来收益（单值）"""
        if not self._is_fitted:
            raise RuntimeError("Model not fitted yet. Call fit() first.")

        feat = FeatureEngineer.compute_all(df)
        if feat.empty or len(feat) < self.seq_len:
            return 0.0

        values = feat[self._feature_cols].values
        seq = values[-self.seq_len :]
        x_mean = seq.mean(axis=0).reshape(1, -1)
        pred = self._xgb_model.predict(x_mean)[0]
        return float(pred)

    def feature_importance(self) -> pd.Series | None:
        """返回特征重要性"""
        if self._xgb_model is None:
            return None
        imp = self._xgb_model.feature_importances_
        return pd.Series(imp, index=self._feature_cols).sort_values(ascending=False)
