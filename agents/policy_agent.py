"""PolicyAgent: answers policy questions and provides guidance."""

from __future__ import annotations

from typing import Any

from memory.models import AgentRole, Plan, PlanStep, Ticket, Trajectory
from agents.base_agent import BaseAgent
from skills.execution_engine import ExecutionEngine


class PolicyAgent(BaseAgent):

    ROLE = AgentRole.POLICY

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(role=self.ROLE, **kwargs)
        self._engine = ExecutionEngine(self.registry, self.agent_id, self.ROLE)

    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        ctx = context or {}
        wm = self._make_working_memory(ticket.ticket_id)

        query = ctx.get("policy_query", ticket.body)
        plan = Plan(
            ticket_id=ticket.ticket_id,
            objective=f"Answer policy question for ticket {ticket.ticket_id[:8]}",
            steps=[
                PlanStep(
                    skill_name="check_policy",
                    inputs={"query": query},
                    expected_output_keys=["policies"],
                    rationale="Retrieve relevant policies for the customer query",
                ),
                PlanStep(
                    skill_name="send_notification",
                    inputs={
                        "customer_id": ticket.customer_id,
                        "message": "We've looked into your policy question. Please see our response in the ticket.",
                        "channel": "email",
                        "ticket_id": ticket.ticket_id,
                    },
                    rationale="Notify customer that a policy answer has been provided",
                ),
            ],
        )

        trajectory = self._engine.execute(plan, wm, ctx)
        self._log_note(ticket.ticket_id, "Policy guidance provided")
        return trajectory
