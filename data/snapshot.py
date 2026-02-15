from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

import json
from loguru import logger

from data.upbit_client import UpbitClient

SNAPSHOT_PATH = Path(__file__).parent / "snapshot.json"


def _save_snapshot(data: dict):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_snapshot() -> dict | None:
    if not SNAPSHOT_PATH.exists():
        return None
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_snapshot(client: UpbitClient):
    balances = client.balances()
    snapshot = {
        "krw": _find_balance(balances, "KRW"),
        "holdings": [],
    }
    for bal in balances:
        currency = bal.get("currency")
        if currency == "KRW":
            continue
        try:
            amount = float(bal.get("balance", 0) or 0)
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            continue
        snapshot["holdings"].append({
            "currency": currency,
            "amount": amount,
        })
    _save_snapshot(snapshot)
    logger.info("Snapshot saved: {} holdings", len(snapshot["holdings"]))
    return snapshot


def load_snapshot():
    return _load_snapshot()


def compare_with_snapshot(client: UpbitClient, snapshot: dict):
    balances = client.balances()
    current_krw = _find_balance(balances, "KRW")
    diff = current_krw - snapshot.get("krw", 0)
    logger.info(
        "KRW balance change since snapshot: {:+.0f} (current {:.0f} / start {:.0f})",
        diff,
        current_krw,
        snapshot.get("krw", 0),
    )
    holdings = snapshot.get("holdings", [])
    for holding in holdings:
        currency = holding["currency"]
        start_amount = holding["amount"]
        current_amount = _find_balance(balances, currency)
        logger.info(
            "Holding {}: start {:.6f} → current {:.6f} (Δ {:+.6f})",
            currency,
            start_amount,
            current_amount,
            current_amount - start_amount,
        )


def _find_balance(balances, currency: str) -> float:
    for bal in balances:
        if bal.get("currency") == currency:
            try:
                return float(bal.get("balance", 0) or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0
