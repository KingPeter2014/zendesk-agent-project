"""Skill: look up an order from the synthetic data store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def lookup_order(order_id: str, **_: Any) -> dict[str, Any]:
    data_path = Path("data/orders.json")
    if not data_path.exists():
        return {"error": "Order database not found. Run synthetic_data/ticket_generator.py first."}
    orders = json.loads(data_path.read_text())
    for o in orders:
        if o.get("order_id", "").startswith(order_id) or o.get("order_id") == order_id:
            return {"found": True, "order": o}
    return {"found": False, "order_id": order_id, "message": "Order not found"}
