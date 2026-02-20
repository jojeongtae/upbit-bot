from __future__ import annotations

import time
from typing import Dict, Any

from loguru import logger

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


class LLMFilter:
    def __init__(self, model: str, min_interval: int = 600):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self.client = OpenAI()
        self.model = model
        self.min_interval = max(0, min_interval)
        self._last_call: Dict[str, float] = {}

    def should_allow(self, market: str, context: Dict[str, Any]) -> bool:
        now = time.time()
        last = self._last_call.get(market, 0)
        if now - last < self.min_interval:
            return True  # skip LLM, allow by default
        self._last_call[market] = now

        prompt = self._build_prompt(market, context)
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
            content = response.output[0].content[0].text.strip().lower()
            logger.info("LLM decision for {}: {}", market, content)
            if "no" in content and "yes" not in content:
                return False
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM filter failed (%s); allowing trade", exc)
            return True

    @staticmethod
    def _build_prompt(market: str, context: Dict[str, Any]) -> str:
        recent_trades = context.get("recent_trades", [])
        trades_text = ", ".join(
            f"{t['result']} ({t['pnl_pct']:+.2f}%)" for t in recent_trades
        ) or "no recent trades"
        text = f"""
You are a crypto risk assistant. Decide whether to execute the proposed trade.
Market: {market}
Current Price: {context.get('price'):.2f}
Range Break %: {context.get('range_pct'):.2f}
Trend: {context.get('trend')}
Recent Trades: {trades_text}
Overall PnL 24h: {context.get('pnl_24h'):+.2f}%
Answer with short 'yes' or 'no' and one short reason.
"""
        return text
