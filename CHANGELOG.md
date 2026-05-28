# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [Unreleased]

### Added
- Event-driven backtest engine with slippage and commission simulation.
- DualMA (momentum) and MeanReversion (RSI + Bollinger Bands) strategies.
- Risk manager with stop-loss, position limit, blacklist, and duplicate-order protection.
- XGBoost-LSTM fusion predictor for return prediction.
- Akshare data provider for A-share market data.
- Mock data provider for reproducible backtesting.
- Comprehensive test suite (38 tests, TDD).
- CLI interface for backtest, analyze, and daily trading.

## [0.1.0] - 2024-06-01

### Added
- Initial release of Investment Agent.
- Modular architecture: Data → Strategy → Risk → Execution.
- Portfolio and account management with PnL tracking.
- Performance metrics: Sharpe, Max Drawdown, Calmar, volatility.
