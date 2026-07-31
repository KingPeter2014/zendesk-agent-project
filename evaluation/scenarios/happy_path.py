"""Happy-path scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from memory.models import TicketCategory, TicketPriority


@dataclass
class Scenario:
    scenario_id: str
    name: str
    ticket_category: str
    ticket_priority: str
    ticket_body: str
    ticket_subject: str
    context: dict = field(default_factory=dict)
    expected_tools: list[str] = field(default_factory=list)
    optimal_steps: int = 2
    expected_outcome: str = "resolved"


HAPPY_PATH_SCENARIOS = [
    Scenario(
        scenario_id="hp_001",
        name="Standard refund request",
        ticket_category=TicketCategory.BILLING_DISPUTE.value,
        ticket_priority=TicketPriority.MEDIUM.value,
        ticket_subject="Refund for order not received",
        ticket_body="I was charged $49.99 for order #abc12345 but the item never arrived. Please refund.",
        context={"order_id": "abc12345", "amount": 49.99},
        expected_tools=["lookup_order", "process_refund", "send_notification"],
        optimal_steps=3,
    ),
    Scenario(
        scenario_id="hp_002",
        name="Policy question - return window",
        ticket_category=TicketCategory.POLICY_QUESTION.value,
        ticket_priority=TicketPriority.LOW.value,
        ticket_subject="Return policy query",
        ticket_body="What is your return policy for electronics?",
        expected_tools=["check_policy", "send_notification"],
        optimal_steps=2,
    ),
    Scenario(
        scenario_id="hp_003",
        name="VIP escalation",
        ticket_category=TicketCategory.VIP_ESCALATION.value,
        ticket_priority=TicketPriority.CRITICAL.value,
        ticket_subject="Urgent VIP complaint",
        ticket_body="I am a long-time VIP customer and my order has been wrong twice. I need this escalated immediately.",
        expected_tools=["escalate_ticket", "send_notification"],
        optimal_steps=2,
        expected_outcome="escalated",
    ),
    Scenario(
        scenario_id="hp_004",
        name="Off-topic redirect",
        ticket_category=TicketCategory.OFF_TOPIC.value,
        ticket_priority=TicketPriority.LOW.value,
        ticket_subject="General enquiry",
        ticket_body="Can you help me write a poem about autumn?",
        expected_tools=["send_notification"],
        optimal_steps=1,
    ),
]
