from __future__ import annotations

from dataclasses import dataclass, field

from pathlib import Path
from typing import List

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: str = "") -> List[str]:
    raw = os.environ.get(key, default)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    access_key: str = env_str("UPBIT_ACCESS_KEY")
    secret_key: str = env_str("UPBIT_SECRET_KEY")
    target_market: str = env_str("TARGET_MARKET", "KRW-BTC")
    target_markets: List[str] = field(default_factory=lambda: env_list("TARGET_MARKETS"))
    base_capital: float = env_float("BASE_CAPITAL", 100000)
    total_capital: float = env_float("TOTAL_CAPITAL", 100000)
    risk_per_trade: float = env_float("RISK_PER_TRADE", 1.0)
    slippage_bps: float = env_float("SLIPPAGE_BPS", 5.0)
    webhook_url: str = env_str("WEBHOOK_URL")
    min_order_krw: float = env_float("MIN_ORDER_KRW", 5000)
    take_profit_pct: float = env_float("TAKE_PROFIT_PCT", 0.03)
    stop_loss_pct: float = env_float("STOP_LOSS_PCT", 0.02)
    top_markets_count: int = env_int("TOP_MARKETS_COUNT", 5)
    market_refresh_hour: int = env_int("MARKET_REFRESH_HOUR", 9)
    llm_model: str = env_str("LLM_MODEL", "gpt-4o-mini")
    llm_min_interval: int = env_int("LLM_MIN_INTERVAL", 600)
    enable_llm_filter: bool = env_str("ENABLE_LLM_FILTER", "1") == "1"

    @property
    def default_market(self) -> str:
        if self.target_markets:
            return self.target_markets[0]
        return self.target_market


settings = Settings()
