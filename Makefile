.PHONY: install install-dev test lint format type check clean docs

PYTHON := python
PIP := pip

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=investment_agent --cov-report=term-missing

test-cov:
	pytest tests/ -v --cov=investment_agent --cov-report=html --cov-report=term-missing

lint:
	ruff check src/ tests/ strategies/

format:
	ruff format src/ tests/ strategies/
	ruff check --select I --fix src/ tests/ strategies/

type:
	mypy src/investment_agent

check: format lint type test

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docs:
	cd docs && make html

run-backtest:
	$(PYTHON) -m investment_agent.main backtest --symbols 000001.SZ 600000.SH --days 180

run-analyze:
	$(PYTHON) -m investment_agent.main analyze --symbol 000001.SZ
