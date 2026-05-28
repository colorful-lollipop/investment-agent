<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blueviolet.svg"/>
  <img src="https://img.shields.io/badge/python-3.10%7C3.11%7C3.12-blue.svg"/>
  <img src="https://img.shields.io/badge/code%20style-ruff-000000.svg"/>
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg"/>
</p>

<h1 align="center">Investment Agent</h1>

<p align="center">
  <b>A modular quantitative investment analysis framework</b><br>
  Backtesting · Risk Management · ML Prediction · A-Share Market
</p>

---

## Features

- **Event-Driven Backtest Engine** — Simulate real trading with slippage, commission, and volume constraints.
- **Multi-Strategy Support** — Built-in DualMA (trend) and MeanReversion (RSI + Bollinger) strategies.
- **Risk-First Design** — Pre-trade risk checks: stop-loss, position limits, blacklist, cooldown.
- **ML Prediction** — XGBoost-LSTM fusion model for return prediction (inspired by academic research).
- **A-Share Data** — Free A-share market data via [Akshare](https://www.akshare.xyz/).
- **TDD & High Coverage** — 38+ unit tests covering core modules.
- **CLI & Config-Driven** — Simple YAML configuration and command-line interface.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/investment-agent.git
cd investment-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Run Backtest

```bash
python -m investment_agent.main backtest --symbols 000001.SZ 600000.SH --days 180
```

### Analyze a Stock

```bash
python -m investment_agent.main analyze --symbol 000001.SZ
```

### Use in Python

```python
from investment_agent import InvestmentAgent

agent = InvestmentAgent.from_config("config/config.yaml")
metrics = agent.backtest(symbols=["000001.SZ"], days=180)
print(metrics)
```

## Project Structure

```
investment-agent/
├── src/investment_agent/    # Core source code
│   ├── core/                # Domain models (Signal, Order, Position, Account)
│   ├── data/                # Data providers (Akshare, Mock)
│   ├── strategy/            # Trading strategies
│   ├── execution/           # Broker & Risk Manager
│   ├── backtest/            # Backtest engine & metrics
│   ├── ml/                  # Feature engineering & prediction
│   └── agent.py             # Main agent orchestrator
├── tests/                   # Test suite (pytest)
├── config/                  # YAML configurations
├── strategies/              # User-defined strategies
├── docs/                    # Documentation
└── examples/                # Usage examples
```

## Development

```bash
# Run all quality checks
make check

# Run tests with coverage
make test-cov

# Format code
make format

# Type checking
make type
```

## Architecture

The system follows a layered architecture inspired by **vnpy**, **Backtrader**, and **Qlib**:

```
DataProvider → Strategy → RiskManager → Broker → Account/Portfolio
                    ↑_________↓
                    Fill callbacks
```

All strategies inherit from `BaseStrategy` and implement `generate_signals()`.
Risk rules are pluggable via `RiskManager.add_rule()`.

## Documentation

- [Architecture Design](docs/ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)

## Disclaimer

**This project is for research and educational purposes only.**
It does not constitute investment advice. Trading involves substantial risk of loss.
Always backtest thoroughly before deploying strategies with real capital.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- [vnpy](https://github.com/vnpy/vnpy) — For the event-driven architecture inspiration.
- [Backtrader](https://www.backtrader.com/) — For the backtesting engine design patterns.
- [Qlib](https://github.com/microsoft/qlib) — For the AI-quantitative research paradigm.
- [Akshare](https://www.akshare.xyz/) — For the free A-share data source.
