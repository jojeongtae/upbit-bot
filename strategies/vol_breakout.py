from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from config import Settings
from data.upbit_client import UpbitClient


@dataclass
class TradeRecord:
    timestamp: str
    action: str
    price: float
    volume: float
    reason: str


class VolatilityBreakout:
    def __init__(self, client: UpbitClient, settings: Settings, k: float = 0.5):
        self.client = client
        self.settings = settings
        self.k = k
        market_split = settings.target_market.split("-")
        if len(market_split) != 2:
            raise ValueError("TARGET_MARKET must be like KRW-BTC")
        self.base_currency, self.quote_currency = market_split
        self.entry_price: Optional[float] = None
        self.trade_log: List[TradeRecord] = []

    def _fetch_candles(self, count: int = 60) -> pd.DataFrame:
        raw = self.client.candles(self.settings.target_market, unit=60, count=count)
        df = pd.DataFrame(raw)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        df.rename(columns={"opening_price": "open", "high_price": "high", "low_price": "low", "trade_price": "close"}, inplace=True)
        return df[["timestamp", "open", "high", "low", "close"]]

    def _signal(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        today_open = df.iloc[-1]["open"]
        range_ = prev["high"] - prev["low"]
        target = today_open + range_ * self.k
        current = df.iloc[-1]["close"]
        if current > target:
            return {"action": "buy", "price": current}
        return None

    def _position_size(self) -> float:
        try:
            return self.client.get_balance(self.quote_currency)
        except Exception:
            logger.warning("Unable to fetch balance; assuming zero position")
            return 0.0

    def _has_position(self) -> bool:
        return self._position_size() > 0

    def _current_price(self) -> Optional[float]:
        try:
            ticker = self.client.ticker(self.settings.target_market)
            return float(ticker.get("trade_price"))
        except Exception as exc:
            logger.warning("Failed to fetch ticker for %s: %s", self.settings.target_market, exc)
            return None

    def _check_exit(self):
        position = self._position_size()
        if position <= 0:
            return None
        current_price = self._current_price()
        if current_price is None:
            return None
        entry = self.entry_price or current_price
        tp_price = entry * (1 + self.settings.take_profit_pct)
        sl_price = entry * (1 - self.settings.stop_loss_pct)

        exit_reason = None
        if current_price >= tp_price:
            exit_reason = "take_profit"
        elif current_price <= sl_price:
            exit_reason = "stop_loss"

        if not exit_reason:
            return None

        try:
            order = self.client.place_market_sell(self.settings.target_market, position)
        except Exception as exc:
            logger.error("Sell order failed: %s", exc)
            return None
        record = TradeRecord(timestamp=str(pd.Timestamp.utcnow()), action="SELL", price=current_price, volume=position, reason=exit_reason)
        self.trade_log.append(record)
        self.entry_price = None
        return {"order": order, "record": record}

    def execute_live(self):
        df = self._fetch_candles(count=2)
        if self._has_position():
            exit_result = self._check_exit()
            if exit_result:
                return exit_result

        signal = self._signal(df)
        if not signal:
            return None

        price = signal["price"]
        adjusted_price = price * (1 + self.settings.slippage_bps / 10000)
        krw_balance = self.client.get_balance(self.base_currency)
        stake = min(self.settings.base_capital, krw_balance)
        if stake < self.settings.min_order_krw:
            logger.warning("Insufficient KRW balance for min order: %.2f < %.2f", stake, self.settings.min_order_krw)
            return None
        volume = round(stake / adjusted_price, 6)
        try:
            order = self.client.place_limit_order("bid", self.settings.target_market, adjusted_price, volume)
        except Exception as exc:
            logger.error("Buy order failed: %s", exc)
            return None
        self.entry_price = adjusted_price
        record = TradeRecord(timestamp=str(df.iloc[-1]["timestamp"]), action="BUY", price=adjusted_price, volume=volume, reason="breakout")
        self.trade_log.append(record)
        return {"order": order, "record": record}

    def run_backtest(self, count: int = 200):
        df = self._fetch_candles(count=count)
        cash = self.settings.base_capital
        position = 0.0
        equity_curve = []
        trades = []
        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            today = df.iloc[i]
            range_ = prev["high"] - prev["low"]
            target = today["open"] + range_ * self.k
            if position == 0 and today["high"] >= target:
                position = cash / target
                cash = 0
                trades.append((today["timestamp"], "buy", target))
            elif position > 0 and today["close"] < today["open"]:
                cash = position * today["close"]
                position = 0
                trades.append((today["timestamp"], "sell", today["close"]))
            equity = cash + position * today["close"]
            equity_curve.append(equity)
        if position > 0:
            cash = position * df.iloc[-1]["close"]
            trades.append((df.iloc[-1]["timestamp"], "sell", df.iloc[-1]["close"]))
        profit = cash - self.settings.base_capital
        equity_series = pd.Series(equity_curve)
        drawdown = (equity_series - equity_series.cummax()) / equity_series.cummax()
        metrics = {
            "final_equity": cash,
            "profit": profit,
            "roi": profit / self.settings.base_capital,
            "max_drawdown": drawdown.min() if not drawdown.empty else 0,
            "trades": trades
        }
        return metrics
