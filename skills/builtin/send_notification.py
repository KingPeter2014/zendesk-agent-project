"""Skill: send a notification to a customer (simulated in demo)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_PATH = Path("data/notifications.jsonl")


def send_notification(
    customer_id: str,
    message: str,
    channel: str = "email",
    ticket_id: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    if channel not in ("email", "sms", "push"):
        return {"success": False, "error": f"Unknown channel: {channel}"}

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "customer_id": customer_id,
        "channel": channel,
        "message": message,
        "ticket_id": ticket_id,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {
        "success": True,
        "customer_id": customer_id,
        "channel": channel,
        "message_preview": message[:80],
        "message": f"Notification sent via {channel} to customer {customer_id[:8]}...",
    }
