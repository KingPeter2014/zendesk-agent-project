"""Skill: process a refund for an order."""

from __future__ import annotations

from typing import Any


REFUND_POLICY_DAYS = 30


def process_refund(order_id: str, amount: float | None = None, reason: str = "customer_request", **_: Any) -> dict[str, Any]:
    # In the demo, all refunds succeed if a valid order_id is present and amount > 0
    if not order_id:
        return {"success": False, "error": "order_id is required"}
    if amount is not None and amount <= 0:
        return {"success": False, "error": "Refund amount must be positive"}

    refund_amount = amount or 0.0
    return {
        "success": True,
        "order_id": order_id,
        "refund_amount": refund_amount,
        "currency": "USD",
        "reason": reason,
        "estimated_days": 5,
        "message": f"Refund of ${refund_amount:.2f} initiated. Funds will appear in 5–7 business days.",
    }
