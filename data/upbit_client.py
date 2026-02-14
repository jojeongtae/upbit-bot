from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

import requests
from loguru import logger

UPBIT_BASE_URL = "https://api.upbit.com/v1"


class UpbitClient:
    def __init__(self, access_key: Optional[str], secret_key: Optional[str]):
        self.access_key = access_key
        self.secret_key = secret_key

    # --- public endpoints -------------------------------------------------
    def candles(self, market: str, unit: int = 60, count: int = 200):
        url = f"{UPBIT_BASE_URL}/candles/minutes/{unit}"
        params = {"market": market, "count": count}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def ticker(self, market: str):
        url = f"{UPBIT_BASE_URL}/ticker"
        resp = requests.get(url, params={"markets": market}, timeout=5)
        resp.raise_for_status()
        return resp.json()[0]

    # --- private endpoints ------------------------------------------------
    def _auth_headers(self, query: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        if not self.access_key or not self.secret_key:
            raise RuntimeError("Private endpoint requires API keys")

        payload = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4())
        }
        if query:
            q = json.dumps(query, separators=(",", ":"), sort_keys=True)
            payload["query"] = q
            m = hashlib.sha512()
            m.update(q.encode())
            payload["query_hash"] = m.hexdigest()
            payload["query_hash_alg"] = "SHA512"

        j = json.dumps(payload).encode()
        token = hmac.new(self.secret_key.encode(), j, hashlib.sha256).hexdigest()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def balances(self):
        url = f"{UPBIT_BASE_URL}/accounts"
        resp = requests.get(url, headers=self._auth_headers(), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_balance(self, currency: str) -> float:
        for bal in self.balances():
            if bal.get("currency") == currency:
                return float(bal.get("balance", 0))
        return 0.0

    def place_limit_order(self, side: str, market: str, price: float, volume: float):
        url = f"{UPBIT_BASE_URL}/orders"
        body = {
            "market": market,
            "side": side,
            "volume": f"{volume:.8f}",
            "price": f"{price:.2f}",
            "ord_type": "limit"
        }
        headers = self._auth_headers(body)
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def place_market_sell(self, market: str, volume: float):
        url = f"{UPBIT_BASE_URL}/orders"
        body = {
            "market": market,
            "side": "ask",
            "volume": f"{volume:.8f}",
            "ord_type": "market"
        }
        headers = self._auth_headers(body)
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        return resp.json()
