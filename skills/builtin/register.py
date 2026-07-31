"""Register all built-in skills into a SkillRegistry instance."""

from __future__ import annotations

from skills.builtin.check_policy import check_policy
from skills.builtin.escalate_ticket import escalate_ticket
from skills.builtin.lookup_order import lookup_order
from skills.builtin.process_refund import process_refund
from skills.builtin.send_notification import send_notification
from skills.registry import SkillMetadata, SkillRegistry


def build_default_registry() -> SkillRegistry:
    registry = SkillRegistry()

    registry.register(
        SkillMetadata(
            name="lookup_order",
            description="Retrieve order details by order ID from the order database.",
            preconditions=["order_id must be provided"],
            side_effects=[],
            input_schema={"order_id": "str"},
            output_schema={"found": "bool", "order": "dict"},
            agent_roles_allowed=["billing", "meta_planner", "supervisor"],
        ),
        lookup_order,
    )

    registry.register(
        SkillMetadata(
            name="process_refund",
            description="Process a refund for an order. Requires order_id and refund amount.",
            preconditions=["order_id must be looked up first", "order must be eligible for refund"],
            side_effects=["creates refund transaction", "sends confirmation email"],
            input_schema={"order_id": "str", "amount": "float", "reason": "str"},
            output_schema={"success": "bool", "refund_amount": "float", "estimated_days": "int"},
            agent_roles_allowed=["billing"],
        ),
        process_refund,
    )

    registry.register(
        SkillMetadata(
            name="check_policy",
            description="Retrieve relevant company policies matching a natural language query.",
            preconditions=[],
            side_effects=[],
            input_schema={"query": "str"},
            output_schema={"policies": "list[dict]"},
            agent_roles_allowed=["policy", "meta_planner", "supervisor"],
        ),
        check_policy,
    )

    registry.register(
        SkillMetadata(
            name="escalate_ticket",
            description="Escalate a ticket to a specialist human agent queue.",
            preconditions=["reason must be documented"],
            side_effects=["creates escalation record", "notifies specialist queue"],
            input_schema={"ticket_id": "str", "reason": "str", "priority": "str", "queue": "str"},
            output_schema={"success": "bool", "escalated_to": "str", "estimated_response_hours": "int"},
            agent_roles_allowed=["escalation", "supervisor", "meta_planner"],
        ),
        escalate_ticket,
    )

    registry.register(
        SkillMetadata(
            name="send_notification",
            description="Send a notification to a customer via email, SMS, or push.",
            preconditions=["customer_id must be valid"],
            side_effects=["records notification log entry"],
            input_schema={"customer_id": "str", "message": "str", "channel": "str"},
            output_schema={"success": "bool"},
            agent_roles_allowed=[],  # any agent
        ),
        send_notification,
    )

    return registry
