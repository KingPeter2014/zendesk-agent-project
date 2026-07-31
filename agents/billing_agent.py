"""BillingAgent: handles refunds, charges, and billing disputes."""

from __future__ import annotations

from typing import Any

from memory.models import AgentRole, Plan, PlanStep, Ticket, Trajectory
from memory.working_memory import WorkingMemory
from agents.base_agent import BaseAgent
from skills.execution_engine import ExecutionEngine


class BillingAgent(BaseAgent):

    ROLE = AgentRole.BILLING

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(role=self.ROLE, **kwargs)
        self._engine = ExecutionEngine(self.registry, self.agent_id, self.ROLE)

    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        ctx = context or {}
        wm = self._make_working_memory(ticket.ticket_id)

        # Build a billing-specific plan
        plan = Plan(
            ticket_id=ticket.ticket_id,
            objective=f"Resolve billing issue for ticket {ticket.ticket_id[:8]}",
            steps=[
                PlanStep(
                    skill_name="lookup_order",
                    inputs={"order_id": ticket.order_id or ctx.get("order_id", "")},
                    expected_output_keys=["order"],
                    rationale="Verify order exists before processing refund",
                ),
                PlanStep(
                    skill_name="process_refund",
                    inputs={
                        "order_id": ticket.order_id or ctx.get("order_id", ""),
                        "amount": ctx.get("amount", 0.0),
                        "reason": "billing_dispute",
                    },
                    expected_output_keys=["success", "refund_amount"],
                    rationale="Issue refund for the disputed charge",
                ),
                PlanStep(
                    skill_name="send_notification",
                    inputs={
                        "customer_id": ticket.customer_id,
                        "message": "Your refund has been processed and will appear in 5–7 business days.",
                        "channel": "email",
                        "ticket_id": ticket.ticket_id,
                    },
                    rationale="Notify customer of refund outcome",
                ),
            ],
        )

        trajectory = self._engine.execute(plan, wm, ctx)
        self._log_note(ticket.ticket_id, f"Billing resolution complete. Outcome: {trajectory.outcome}")
        return trajectory
