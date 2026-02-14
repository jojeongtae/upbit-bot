from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import requests

UPBIT_BASE = "https://api.upbit.com/v1"


def fetch_candles(market: str, unit: int, to: datetime, count: int = 200):
    url = f"{UPBIT_BASE}/candles/minutes/{unit}"
    params = {
        "market": market,
        "count": count,
        "to": to.strftime("%Y-%m-%d %H:%M:%S")
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("market", default="KRW-BTC")
    parser.add_argument("--unit", type=int, default=60)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", default="data/candles.csv")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    to = datetime.utcnow()
    total_needed = args.days * (60 // args.unit) * 24 if args.unit < 60 else args.days * (24 * 60 // args.unit)
    total_needed = max(total_needed, 1)

    while len(all_rows) < total_needed:
        batch = fetch_candles(args.market, args.unit, to, count=200)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1]["timestamp"]
        to = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%S%z") - timedelta(minutes=args.unit)

    # deduplicate & sort
    seen = set()
    cleaned = []
    for row in all_rows:
        key = row["timestamp"]
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)
    cleaned.sort(key=lambda r: r["timestamp"])

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for row in cleaned:
            writer.writerow([
                row["timestamp"],
                row["opening_price"],
                row["high_price"],
                row["low_price"],
                row["trade_price"],
                row["candle_acc_trade_volume"]
            ])

    print(f"Saved {len(cleaned)} rows to {out_path}")


if __name__ == "__main__":
    main()
