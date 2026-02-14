from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class Settings:
    access_key: str = env_str("UPBIT_ACCESS_KEY")
    secret_key: str = env_str("UPBIT_SECRET_KEY")
    target_market: str = env_str("TARGET_MARKET", "KRW-BTC")
    base_capital: float = env_float("BASE_CAPITAL", 100000)
    risk_per_trade: float = env_float("RISK_PER_TRADE", 1.0)
    slippage_bps: float = env_float("SLIPPAGE_BPS", 5.0)
    webhook_url: str = env_str("WEBHOOK_URL")
    min_order_krw: float = env_float("MIN_ORDER_KRW", 5000)
    take_profit_pct: float = env_float("TAKE_PROFIT_PCT", 0.03)
    stop_loss_pct: float = env_float("STOP_LOSS_PCT", 0.02)


settings = Settings()
