"""Skill: retrieve relevant company policies for a query."""

from __future__ import annotations

from typing import Any


POLICIES: dict[str, str] = {
    "return_standard": "Items can be returned within 30 days of delivery for a full refund.",
    "return_electronics": "Electronics have a 14-day return window. Original packaging required.",
    "refund_timeline": "Refunds are processed within 5–7 business days after the return is received.",
    "price_match": "We match competitor prices within 14 days of purchase. Contact support with proof of lower price.",
    "warranty": "All products carry a 12-month manufacturer warranty against defects.",
    "exchange": "Items can be exchanged for a different colour or size within 30 days of delivery.",
    "vip_shipping": "VIP members receive free expedited shipping on all orders over $50.",
    "cancel_order": "Orders can be cancelled before dispatch. Contact support immediately after placing the order.",
    "subscription_cancel": "Subscriptions can be cancelled at any time. Access continues until the end of the billing period.",
}

KEYWORD_MAP: dict[str, list[str]] = {
    "return": ["return_standard", "return_electronics"],
    "refund": ["return_standard", "refund_timeline"],
    "timeline": ["refund_timeline"],
    "price": ["price_match"],
    "match": ["price_match"],
    "warranty": ["warranty"],
    "exchange": ["exchange"],
    "swap": ["exchange"],
    "colour": ["exchange"],
    "color": ["exchange"],
    "vip": ["vip_shipping"],
    "shipping": ["vip_shipping"],
    "cancel": ["cancel_order", "subscription_cancel"],
    "subscription": ["subscription_cancel"],
}


def check_policy(query: str, **_: Any) -> dict[str, Any]:
    query_lower = query.lower()
    matched_keys: set[str] = set()
    for keyword, policy_keys in KEYWORD_MAP.items():
        if keyword in query_lower:
            matched_keys.update(policy_keys)

    if not matched_keys:
        matched_keys = set(POLICIES.keys())

    results = [{"policy_id": k, "text": POLICIES[k]} for k in matched_keys if k in POLICIES]
    return {
        "query": query,
        "policies_found": len(results),
        "policies": results,
    }
