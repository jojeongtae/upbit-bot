from __future__ import annotations

import argparse
import time
from datetime import datetime

from loguru import logger

from config import settings
from data.upbit_client import UpbitClient
from strategies.vol_breakout import VolatilityBreakout
from utils import notify


def run_live(poll_interval: int = 60):
    client = UpbitClient(settings.access_key, settings.secret_key)
    strategy = VolatilityBreakout(client, settings)

    logger.info("Starting live trading loop for {}", settings.target_market)
    while True:
        try:
            result = strategy.execute_live()
            if result:
                logger.info("Trade executed: {}", result)
                notify(settings.webhook_url, {
                    "content": f"{settings.target_market} {result['record'].action} {result['record'].volume:.6f} @ {result['record'].price:.2f} ({result['record'].reason})"
                })
        except Exception as exc:
            logger.exception("Live loop error: {}", exc)
            notify(settings.webhook_url, {"content": f"Live loop error: {exc}"})
        time.sleep(poll_interval)


def run_backtest(count: int = 400):
    client = UpbitClient(None, None)
    strategy = VolatilityBreakout(client, settings)
    metrics = strategy.run_backtest(count=count)
    logger.info("Backtest result: {}", metrics)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "backtest"], default="backtest")
    parser.add_argument("--interval", type=int, default=60, help="poll interval seconds")
    parser.add_argument("--count", type=int, default=400, help="backtest candle count")
    args = parser.parse_args()

    logger.add("logs/{time}.log", rotation="1 day")

    try:
        if args.mode == "live":
            run_live(args.interval)
        else:
            run_backtest(args.count)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        notify(settings.webhook_url, {"content": f"Upbit bot crashed: {exc}"})


if __name__ == "__main__":
    main()
