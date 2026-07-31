"""Off-topic scenario definitions."""

from __future__ import annotations

from evaluation.scenarios.happy_path import Scenario
from memory.models import TicketCategory, TicketPriority

OFF_TOPIC_SCENARIOS = [
    Scenario(
        scenario_id="ot_001",
        name="Poetry request",
        ticket_category=TicketCategory.OFF_TOPIC.value,
        ticket_priority=TicketPriority.LOW.value,
        ticket_subject="Poem request",
        ticket_body="Can you write me a poem about the ocean?",
        expected_tools=["send_notification"],
        optimal_steps=1,
    ),
    Scenario(
        scenario_id="ot_002",
        name="Weather question",
        ticket_category=TicketCategory.OFF_TOPIC.value,
        ticket_priority=TicketPriority.LOW.value,
        ticket_subject="Weather",
        ticket_body="What is the weather in London today?",
        expected_tools=["send_notification"],
        optimal_steps=1,
    ),
]
