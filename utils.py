from __future__ import annotations

import json
import time
from typing import Any, Dict

import requests
from loguru import logger


def notify(webhook_url: str, payload: Dict[str, Any]):
    if not webhook_url:
        return
    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=5)
            resp.raise_for_status()
            break
        except Exception as exc:
            logger.warning("Webhook send failed (%s/%s): %s", attempt + 1, 3, exc)
            time.sleep(2)
