"""EscalationAgent: handles VIP complaints, legal issues, and unresolvable tickets."""

from __future__ import annotations

from typing import Any

from memory.models import AgentRole, OutcomeType, Plan, PlanStep, Ticket, Trajectory
from agents.base_agent import BaseAgent
from skills.execution_engine import ExecutionEngine


class EscalationAgent(BaseAgent):

    ROLE = AgentRole.ESCALATION

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(role=self.ROLE, **kwargs)
        self._engine = ExecutionEngine(self.registry, self.agent_id, self.ROLE)

    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        ctx = context or {}
        wm = self._make_working_memory(ticket.ticket_id)

        reason = ctx.get("reason", "Complex issue requiring specialist review")
        queue = ctx.get("queue", "vip" if ticket.priority.value in ("high", "critical") else "default")

        plan = Plan(
            ticket_id=ticket.ticket_id,
            objective=f"Escalate ticket {ticket.ticket_id[:8]} to specialist",
            steps=[
                PlanStep(
                    skill_name="escalate_ticket",
                    inputs={
                        "ticket_id": ticket.ticket_id,
                        "reason": reason,
                        "priority": ticket.priority.value,
                        "queue": queue,
                    },
                    expected_output_keys=["success", "escalated_to"],
                    rationale="Route ticket to appropriate specialist queue",
                ),
                PlanStep(
                    skill_name="send_notification",
                    inputs={
                        "customer_id": ticket.customer_id,
                        "message": "Your case has been escalated to a senior specialist. We will respond within 4 hours.",
                        "channel": "email",
                        "ticket_id": ticket.ticket_id,
                    },
                    rationale="Inform customer of escalation and expected response time",
                ),
            ],
        )

        trajectory = self._engine.execute(plan, wm, ctx)
        # Escalated tickets resolve with ESCALATED outcome
        trajectory.outcome = OutcomeType.ESCALATED
        self._log_note(ticket.ticket_id, f"Ticket escalated to {queue} queue. Reason: {reason}")
        return trajectory

    def _delegation_succeeded(self, _trajectory: Trajectory) -> bool:
        return True  # escalation itself always succeeds
