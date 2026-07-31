"""How eval_set.json was generated — WITH the planted leak.

Each query is a verbatim substring of the policy text it's meant to test
retrieval against, so the eval set is not independent of the corpus it's
scored against. Kept here for transparency/reproducibility; not part of the
candidate-facing exercise and not meant to be run during it.

    python practice/policy_retrieval/solutions/generate_eval_set_leaky.py
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# policy_id -> verbatim substrings lifted directly from that policy's own text
LEAKY_SUBSTRINGS: dict[str, list[str]] = {
    "pol_return_30": [
        "returned within 30 days of delivery for a full refund",
        "Items can be returned within 30 days",
    ],
    "pol_return_electronics": [
        "Electronics have a 14-day return window",
        "Original packaging required",
    ],
    "pol_refund_timeline": [
        "Refunds are processed within 5–7 business days",
        "processed within 5–7 business days after return is received",
    ],
    "pol_price_match": [
        "match competitor prices within 14 days of purchase",
        "Contact support with proof",
    ],
    "pol_warranty": [
        "12-month manufacturer warranty against defects",
        "All products carry a 12-month manufacturer warranty",
    ],
    "pol_exchange": [
        "exchanged for a different colour or size",
        "Items can be exchanged",
    ],
    "pol_vip_shipping": [
        "VIP members receive free expedited shipping",
        "free expedited shipping on all orders",
    ],
    "pol_cancel_order": [
        "Orders can be cancelled before dispatch",
        "Contact support immediately",
    ],
    "pol_subscription_cancel": [
        "Subscriptions can be cancelled at any time",
        "Access continues until the end of the billing period",
    ],
    "pol_gift_card": [
        "Gift cards do not expire",
        "used towards any purchase, including sale items",
    ],
}


def main() -> None:
    eval_set = [
        {"query": query, "expected_policy_id": policy_id}
        for policy_id, queries in LEAKY_SUBSTRINGS.items()
        for query in queries
    ]
    out_path = BASE_DIR / "eval_set.json"
    with open(out_path, "w") as f:
        json.dump(eval_set, f, indent=2)
    print(f"Wrote {len(eval_set)} leaky eval queries to {out_path}")


if __name__ == "__main__":
    main()
