"""特征工程 —— 参考 Qlib Alpha158 / 金融大牛经验
核心特征：MA、RSI、MACD、布林带、波动率、量价关系
"""

import pandas as pd


class FeatureEngineer:
    """技术指标特征工程器"""

    @staticmethod
    def compute_all(df: pd.DataFrame) -> pd.DataFrame:
        """输入OHLCV DataFrame，输出特征矩阵"""
        feat = pd.DataFrame(index=df.index)
        close = df["close"]
        volume = df["volume"]

        # 价格特征
        feat["returns_1d"] = close.pct_change()
        feat["returns_5d"] = close.pct_change(5)
        feat["returns_10d"] = close.pct_change(10)
        feat["returns_20d"] = close.pct_change(20)

        # 均线偏离
        for window in [5, 10, 20, 60]:
            ma = close.rolling(window).mean()
            feat[f"ma_dist_{window}"] = (close - ma) / ma

        # RSI
        feat["rsi_14"] = FeatureEngineer._rsi(close, 14)

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        feat["macd"] = ema12 - ema26
        feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()

        # 布林带
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        feat["bb_width"] = (std20 * 2) / ma20
        feat["bb_position"] = (close - (ma20 - std20 * 2)) / (std20 * 4)

        # 波动率
        feat["volatility_5d"] = close.pct_change().rolling(5).std()
        feat["volatility_20d"] = close.pct_change().rolling(20).std()

        # 量价特征
        feat["volume_ma_ratio"] = volume / volume.rolling(20).mean()
        feat["volume_std_20d"] = volume.rolling(20).std() / volume.rolling(20).mean()

        # 高低价特征
        feat["high_low_ratio"] = (df["high"] - df["low"]) / close
        feat["open_close_ratio"] = (df["open"] - close) / close

        # 目标：未来5日收益率（用于监督学习）
        feat["target_5d"] = close.pct_change(5).shift(-5)

        return feat.dropna()

    @staticmethod
    def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / window, min_periods=window).mean()
        avg_loss = loss.ewm(alpha=1 / window, min_periods=window).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
