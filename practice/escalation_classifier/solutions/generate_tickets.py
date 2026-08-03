"""Regenerates tickets.json. Deterministic (seeded) — rerun to reproduce.

    python practice/escalation_classifier/solutions/generate_tickets.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

CATEGORIES = ["billing_dispute", "order_issue", "policy_question", "vip_escalation", "off_topic"]
PRIORITIES = ["low", "medium", "high", "critical"]
TIERS = ["standard", "premium", "vip"]

N_TICKETS = 220
OUT_PATH = Path(__file__).parent.parent / "tickets.json"


def make_ticket(i: int, rng: random.Random) -> dict:
    category = rng.choice(CATEGORIES)
    priority = rng.choices(PRIORITIES, weights=[0.35, 0.35, 0.2, 0.1])[0]
    tier = rng.choices(TIERS, weights=[0.6, 0.3, 0.1])[0]
    body_length = max(20, int(rng.gauss(180, 60)))

    # Intake-time signal for whether this ticket *should* be escalated,
    # with noise -- a real, learnable-but-imperfect pattern.
    score = 0.0
    if category == "vip_escalation":
        score += 0.6
    if priority in ("high", "critical") and tier == "vip":
        score += 0.5
    if priority == "critical":
        score += 0.2
    if tier == "vip":
        score += 0.1
    score += rng.uniform(-0.3, 0.3)
    escalated = score > 0.5

    # assigned_team is set by the routing system AFTER the escalation
    # decision is made -- not known at ticket intake time, when a
    # prediction would actually need to run. Small mislabel rate so it
    # isn't a literal 1:1 encoding of the label.
    if rng.random() < 0.03:
        assigned_team = "general_support" if escalated else "escalation_specialists"
    else:
        assigned_team = "escalation_specialists" if escalated else "general_support"

    return {
        "ticket_id": f"T{i:04d}",
        "category": category,
        "priority": priority,
        "customer_tier": tier,
        "body_length": body_length,
        "assigned_team": assigned_team,
        "escalated": escalated,
    }


def main() -> None:
    rng = random.Random(42)
    tickets = [make_ticket(i, rng) for i in range(N_TICKETS)]
    OUT_PATH.write_text(json.dumps(tickets, indent=2))
    print(f"Wrote {len(tickets)} tickets to {OUT_PATH}")
    print(f"Escalation rate: {sum(t['escalated'] for t in tickets) / len(tickets):.2%}")


if __name__ == "__main__":
    main()