from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import requests
from loguru import logger

UPBIT_BASE_URL = "https://api.upbit.com/v1"


def _chunked(seq: List[str], size: int) -> List[List[str]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


class MarketSelector:
    """Selects top-K markets by 24h traded value and refreshes daily."""

    def __init__(
        self,
        top_n: int,
        refresh_hour_kst: int,
        fallback_markets: Optional[List[str]] = None,
    ) -> None:
        self.top_n = top_n
        self.refresh_hour = refresh_hour_kst
        self.fallback_markets = fallback_markets or []
        self.current_markets: List[str] = []
        self.last_refresh: Optional[datetime] = None
        self.session = requests.Session()
        self.refresh(force=True)

    @staticmethod
    def _now_kst() -> datetime:
        return datetime.utcnow() + timedelta(hours=9)

    def _should_refresh(self) -> bool:
        if not self.current_markets or not self.last_refresh:
            return True
        now = self._now_kst()
        last = self.last_refresh
        # Refresh after refresh_hour each new KST day
        if now.date() != last.date() and now.hour >= self.refresh_hour:
            return True
        # Safety: refresh if more than 24h elapsed
        if (now - last).total_seconds() > 24 * 3600:
            return True
        return False

    def maybe_refresh(self) -> List[str]:
        if self._should_refresh():
            return self.refresh()
        return self.current_markets

    def refresh(self, force: bool = False) -> List[str]:
        if not force and not self._should_refresh():
            return self.current_markets

        try:
            markets = self._fetch_top_markets()
            if markets:
                self.current_markets = markets
                self.last_refresh = self._now_kst()
                logger.info("Selected markets: {}", ", ".join(self.current_markets))
            elif self.fallback_markets:
                logger.warning("Market fetch empty; falling back to predefined list")
                self.current_markets = self.fallback_markets
                self.last_refresh = self._now_kst()
            else:
                logger.error("Market fetch empty and no fallback available")
        except Exception as exc:  # pragma: no cover
            logger.exception("Market selection failed: %s", exc)
            if self.fallback_markets:
                self.current_markets = self.fallback_markets
        return self.current_markets

    def _fetch_top_markets(self) -> List[str]:
        resp = self.session.get(f"{UPBIT_BASE_URL}/market/all", params={"isDetails": "false"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        krw_markets = [item["market"] for item in data if item.get("market", "").startswith("KRW-")]
        if not krw_markets:
            return []

        market_stats = []
        for chunk in _chunked(krw_markets, 20):
            ticker_resp = self.session.get(
                f"{UPBIT_BASE_URL}/ticker",
                params={"markets": ",".join(chunk)},
                timeout=10,
            )
            ticker_resp.raise_for_status()
            for item in ticker_resp.json():
                market = item.get("market")
                acc_price = float(item.get("acc_trade_price_24h", 0))
                if market:
                    market_stats.append((market, acc_price))

        market_stats.sort(key=lambda x: x[1], reverse=True)
        selected = [m for m, _ in market_stats[: self.top_n]]
        return selected or self.fallback_markets
