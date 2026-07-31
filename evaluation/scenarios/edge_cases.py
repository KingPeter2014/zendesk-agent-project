"""Edge case scenarios: missing order IDs, ambiguous requests, concurrent access."""

from __future__ import annotations

from evaluation.scenarios.happy_path import Scenario
from memory.models import TicketCategory, TicketPriority

EDGE_CASE_SCENARIOS = [
    Scenario(
        scenario_id="edge_001",
        name="Missing order ID",
        ticket_category=TicketCategory.BILLING_DISPUTE.value,
        ticket_priority=TicketPriority.MEDIUM.value,
        ticket_subject="Charge without order number",
        ticket_body="I was charged but I don't know my order number. Can you refund me?",
        expected_tools=["send_notification"],  # can't refund without order_id
        optimal_steps=1,
        expected_outcome="clarification_needed",
    ),
    Scenario(
        scenario_id="edge_002",
        name="Non-existent order ID",
        ticket_category=TicketCategory.ORDER_ISSUE.value,
        ticket_priority=TicketPriority.MEDIUM.value,
        ticket_subject="Order not found",
        ticket_body="Order #zzz99999 has not arrived.",
        context={"order_id": "zzz99999"},
        expected_tools=["lookup_order"],
        optimal_steps=1,
    ),
    Scenario(
        scenario_id="edge_003",
        name="Ambiguous complaint",
        ticket_category=TicketCategory.ORDER_ISSUE.value,
        ticket_priority=TicketPriority.MEDIUM.value,
        ticket_subject="Something is wrong",
        ticket_body="Something is not right with my account. Please fix it.",
        expected_tools=["send_notification"],
        optimal_steps=1,
        expected_outcome="clarification_needed",
    ),
    Scenario(
        scenario_id="edge_004",
        name="Multiple issues in one ticket",
        ticket_category=TicketCategory.BILLING_DISPUTE.value,
        ticket_priority=TicketPriority.HIGH.value,
        ticket_subject="Billing and delivery issue",
        ticket_body="My order #def67890 arrived damaged AND I was charged twice. Need refund and replacement.",
        context={"order_id": "def67890", "amount": 79.99},
        expected_tools=["lookup_order", "process_refund", "send_notification"],
        optimal_steps=3,
    ),
]
