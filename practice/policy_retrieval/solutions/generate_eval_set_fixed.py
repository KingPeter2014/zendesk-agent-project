"""Example of a FIXED eval set: paraphrased, realistic customer queries that
are NOT copy-pasted from the policy text.

This is what a strong candidate's fix should look like in shape (exact
wording may differ) — an eval set that is independent of the corpus it's
scored against. Writes to eval_set_fixed_example.json, alongside (not
overwriting) the original leaky eval_set.json.

    python practice/policy_retrieval/solutions/generate_eval_set_fixed.py
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

PARAPHRASED_EVAL_SET: list[dict[str, str]] = [
    {"query": "How long do I have to send something back for a refund?", "expected_policy_id": "pol_return_30"},
    {"query": "Can I get my money back if I'm not happy with an order?", "expected_policy_id": "pol_return_30"},
    {"query": "What's the return window for a laptop I bought?", "expected_policy_id": "pol_return_electronics"},
    {"query": "Do I need the original box to return my headphones?", "expected_policy_id": "pol_return_electronics"},
    {"query": "How long until I see my refund in my account?", "expected_policy_id": "pol_refund_timeline"},
    {"query": "When does the refund clock start counting?", "expected_policy_id": "pol_refund_timeline"},
    {"query": "I found this item cheaper somewhere else, can you match it?", "expected_policy_id": "pol_price_match"},
    {"query": "Do you offer price matching against competitors?", "expected_policy_id": "pol_price_match"},
    {"query": "Is my blender covered if it breaks after a year?", "expected_policy_id": "pol_warranty"},
    {"query": "What's your warranty policy on defective products?", "expected_policy_id": "pol_warranty"},
    {"query": "Can I swap this shirt for a bigger size?", "expected_policy_id": "pol_exchange"},
    {"query": "I want a different colour, not a refund — is that possible?", "expected_policy_id": "pol_exchange"},
    {"query": "Do VIP members get faster delivery?", "expected_policy_id": "pol_vip_shipping"},
    {"query": "Is expedited shipping free for VIP customers?", "expected_policy_id": "pol_vip_shipping"},
    {"query": "Can I cancel my order before it ships?", "expected_policy_id": "pol_cancel_order"},
    {"query": "I just placed an order by mistake, can I stop it?", "expected_policy_id": "pol_cancel_order"},
    {"query": "How do I stop my monthly subscription?", "expected_policy_id": "pol_subscription_cancel"},
    {"query": "If I cancel today, do I lose access right away?", "expected_policy_id": "pol_subscription_cancel"},
    {"query": "Do gift cards ever expire?", "expected_policy_id": "pol_gift_card"},
    {"query": "Can I use a gift card on items that are on sale?", "expected_policy_id": "pol_gift_card"},
]


def main() -> None:
    out_path = BASE_DIR / "eval_set_fixed_example.json"
    with open(out_path, "w") as f:
        json.dump(PARAPHRASED_EVAL_SET, f, indent=2)
    print(f"Wrote {len(PARAPHRASED_EVAL_SET)} paraphrased eval queries to {out_path}")


if __name__ == "__main__":
    main()
