"""SupervisorAgent: monitors execution, enforces guardrails, mediates escalations."""

from __future__ import annotations

from typing import Any

from memory.models import (
    AgentRole, AgentStep, OutcomeType, Plan, PlanStep, Ticket, Trajectory,
)
from agents.base_agent import BaseAgent


ALLOWED_SKILLS_BY_ROLE: dict[str, set[str]] = {
    "billing": {"lookup_order", "process_refund", "send_notification"},
    "policy": {"check_policy", "send_notification"},
    "escalation": {"escalate_ticket", "send_notification"},
    "meta_planner": {"lookup_order", "check_policy", "escalate_ticket", "send_notification"},
}


class SupervisorAgent(BaseAgent):

    ROLE = AgentRole.SUPERVISOR

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(role=self.ROLE, **kwargs)

    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        # Supervisor does not process tickets directly; it wraps other agents
        raise NotImplementedError("SupervisorAgent wraps other agents; use supervise() instead")

    def supervise(
        self,
        plan: Plan,
        executing_agent_role: str,
        ticket: Ticket,
        trajectory: Trajectory,
    ) -> tuple[bool, str]:
        """
        Review a completed trajectory for policy violations.
        Returns (approved: bool, reason: str).
        """
        allowed = ALLOWED_SKILLS_BY_ROLE.get(executing_agent_role, set())
        violations = []

        for step in trajectory.steps:
            for tc in step.tool_calls:
                if allowed and tc.tool_name not in allowed:
                    violations.append(
                        f"Agent '{executing_agent_role}' used skill '{tc.tool_name}' outside its allowed set"
                    )

        if violations:
            self._log_note(ticket.ticket_id, f"Supervisor violations: {violations}")
            return False, "; ".join(violations)

        return True, "OK"

    def check_tool_allowed(self, agent_role: str, skill_name: str) -> bool:
        allowed = ALLOWED_SKILLS_BY_ROLE.get(agent_role)
        if allowed is None:
            return True  # unknown role: permissive
        return skill_name in allowed
