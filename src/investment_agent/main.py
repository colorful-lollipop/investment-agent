"""Investment Agent CLI 入口
用法:
    python src/main.py backtest --symbols 000001.SZ 600000.SH --days 180
    python src/main.py analyze --symbol 000001.SZ
    python src/main.py daily --symbols 000001.SZ 600000.SH
"""

import argparse

from investment_agent.agent import InvestmentAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Investment Analysis Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # backtest
    p_backtest = subparsers.add_parser("backtest", help="Run backtest")
    p_backtest.add_argument("--symbols", nargs="+", required=True, help="Stock symbols")
    p_backtest.add_argument("--days", type=int, default=180, help="Backtest days")
    p_backtest.add_argument("--config", default="config/config.yaml", help="Config file")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a single stock")
    p_analyze.add_argument("--symbol", required=True, help="Stock symbol")
    p_analyze.add_argument("--config", default="config/config.yaml", help="Config file")

    # daily
    p_daily = subparsers.add_parser("daily", help="Run daily trading loop")
    p_daily.add_argument("--symbols", nargs="+", required=True, help="Stock symbols")
    p_daily.add_argument("--config", default="config/config.yaml", help="Config file")

    args = parser.parse_args()
    agent = InvestmentAgent.from_config(args.config)

    if args.command == "backtest":
        print(f"Running backtest for {args.symbols} over {args.days} days...")
        metrics = agent.backtest(symbols=args.symbols, days=args.days)
        print(metrics)
    elif args.command == "analyze":
        result = agent.analyze(args.symbol)
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif args.command == "daily":
        result = agent.run_daily(args.symbols)
        print(f"Daily run result: {result}")


if __name__ == "__main__":
    main()
