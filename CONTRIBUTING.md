# Contributing to Investment Agent

Thank you for your interest in contributing! This document provides guidelines for participating in the project.

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/investment-agent.git
cd investment-agent

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install
```

## Code Quality

We enforce code quality through automated tools:

```bash
# Format and lint
make format        # ruff format
make lint          # ruff check

# Type checking
make type          # mypy

# Run tests with coverage
make test          # pytest

# Run all checks
make check
```

## Pull Request Process

1. **Create an Issue** first for major changes (features, refactors).
2. **Fork** the repository and create a feature branch from `main`.
3. **Write tests** for new functionality (TDD preferred).
4. **Ensure all checks pass**: `make check`.
5. **Update documentation** if you change APIs or behavior.
6. **Submit PR** with a clear description and link to the issue.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new risk rule for liquidity check
fix: correct drawdown calculation in backtest engine
docs: update README with installation instructions
test: add integration tests for akshare provider
refactor: simplify signal generation in DualMAStrategy
```

## Reporting Bugs

Please use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) and include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Error logs or traceback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
