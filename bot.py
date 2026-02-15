from __future__ import annotations

import argparse
import time
from datetime import datetime

from loguru import logger

from config import settings
from data.upbit_client import UpbitClient
from market_selector import MarketSelector
from strategies.vol_breakout import VolatilityBreakout
from utils import notify


def _find_balance(balances, currency: str) -> float:
    for bal in balances:
        if bal.get("currency") == currency:
            try:
                return float(bal.get("balance", 0) or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def run_live(poll_interval: int = 60, status_every: int = 10):
    client = UpbitClient(settings.access_key, settings.secret_key)
    fallback_markets = settings.target_markets or [settings.target_market]
    selector = MarketSelector(
        top_n=settings.top_markets_count,
        refresh_hour_kst=settings.market_refresh_hour,
        fallback_markets=fallback_markets,
    )
    desired_markets = selector.current_markets or fallback_markets
    strategies: dict[str, VolatilityBreakout] = {}

    def sync_strategies(markets: list[str]) -> None:
        nonlocal strategies
        if not markets:
            return
        total_capital = settings.total_capital or settings.base_capital
        capital_per = max(total_capital / len(markets), settings.min_order_krw)
        new_strategies: dict[str, VolatilityBreakout] = {}
        for market in markets:
            if market in strategies:
                strat = strategies[market]
                strat.update_capital(capital_per)
                strat.set_active(True)
            else:
                strat = VolatilityBreakout(client, settings, market=market, capital_per_trade=capital_per)
            new_strategies[market] = strat
        # keep old strategies that still hold a position so we can exit gracefully
        for market, strat in strategies.items():
            if market in new_strategies:
                continue
            if strat.has_open_position():
                strat.set_active(False)
                new_strategies[market] = strat
                logger.info("Maintaining {} until position closes", market)
        strategies = new_strategies

    sync_strategies(desired_markets)

    logger.info("Starting live trading loop for dynamic markets: {}", ", ".join(strategies.keys()))
    loop_count = 0
    while True:
        try:
            desired_markets = selector.maybe_refresh()
            if not desired_markets:
                desired_markets = fallback_markets
            if set(m.upper() for m in desired_markets) != set(strategies.keys()):
                sync_strategies(desired_markets)
                logger.info("Updated market basket: {}", ", ".join(strategies.keys()))

            if not strategies:
                logger.warning("No active strategies; sleeping")
                time.sleep(poll_interval)
                continue

            for market, strategy in strategies.items():
                result = strategy.execute_live()
                if result:
                    record = result["record"]
                    logger.info(
                        "Trade executed [{}]: {} {} @ {:.2f} ({})",
                        result.get("market", market),
                        record.action,
                        record.volume,
                        record.price,
                        record.reason,
                    )
                    notify(
                        settings.webhook_url,
                        {
                            "content": f"{result.get('market', market)} {record.action} {record.volume:.6f} @ {record.price:.2f} ({record.reason})",
                        },
                    )

            loop_count += 1
            if loop_count % status_every == 0:
                balances = client.balances()
                krw_balance = _find_balance(balances, "KRW")
                logger.info("Status: KRW balance = {:.2f}", krw_balance)
                for market, strategy in strategies.items():
                    coin_balance = _find_balance(balances, strategy.quote_currency)
                    try:
                        ticker = client.ticker(market)
                        price = ticker.get("trade_price", 0)
                    except Exception as exc:
                        price = 0
                        logger.warning("Ticker fetch failed for %s: %s", market, exc)
                    logger.info(
                        "Status [{}]: {}={:.6f}, price={:.0f}",
                        market,
                        strategy.quote_currency,
                        coin_balance,
                        price,
                    )
        except Exception as exc:
            logger.exception("Live loop error: {}", exc)
            notify(settings.webhook_url, {"content": f"Live loop error: {exc}"})
        time.sleep(poll_interval)


def run_backtest(count: int = 400, market: str | None = None):
    client = UpbitClient(None, None)
    strategy = VolatilityBreakout(client, settings, market=market or settings.default_market)
    metrics = strategy.run_backtest(count=count)
    logger.info("Backtest result: {}", metrics)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "backtest"], default="backtest")
    parser.add_argument("--interval", type=int, default=60, help="poll interval seconds")
    parser.add_argument("--count", type=int, default=400, help="backtest candle count")
    parser.add_argument("--status_every", type=int, default=10, help="status log frequency in loops")
    parser.add_argument("--market", type=str, default=None, help="market code for backtest")
    args = parser.parse_args()

    logger.add("logs/{time}.log", rotation="1 day")

    try:
        if args.mode == "live":
            run_live(args.interval, args.status_every)
        else:
            run_backtest(args.count, args.market)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        notify(settings.webhook_url, {"content": f"Upbit bot crashed: {exc}"})


if __name__ == "__main__":
    main()
