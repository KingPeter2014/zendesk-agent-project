"""Governance guardrails: goal alignment, reward hacking detection, approval workflows."""

from __future__ import annotations

from typing import Any

from memory.models import GuardrailEvent, Plan, Ticket


SENSITIVE_SKILLS = {"process_refund", "escalate_ticket"}
MAX_REFUND_NO_APPROVAL = 500.0  # USD


class GovernanceGuardrails:

    def __init__(self) -> None:
        self._events: list[GuardrailEvent] = []
        self._pending_approvals: list[dict[str, Any]] = []

    def check_plan_alignment(self, ticket: Ticket, plan: Plan) -> dict[str, Any]:
        """
        Simple goal-alignment check: ensure the plan objective is relevant
        to the ticket category. Flags divergence as a governance concern.
        """
        category = ticket.category.value
        objective_lower = plan.objective.lower()

        misalignment_signals = {
            "billing_dispute": ["delete", "wipe", "all orders", "all users"],
            "policy_question": ["refund all", "cancel all"],
            "off_topic": ["process_refund", "escalate"],
        }

        flagged = []
        for signal in misalignment_signals.get(category, []):
            if signal in objective_lower:
                flagged.append(signal)

        if flagged:
            event = GuardrailEvent(
                guardrail_type="governance",
                trigger="goal_misalignment",
                severity="high",
                original_text=plan.objective[:200],
                action_taken="flagged",
                ticket_id=ticket.ticket_id,
            )
            self._events.append(event)
            return {"aligned": False, "signals": flagged, "event": event.model_dump(mode="json")}

        return {"aligned": True}

    def check_high_value_action(
        self,
        skill_name: str,
        inputs: dict[str, Any],
        ticket_id: str,
    ) -> dict[str, Any]:
        """Require human approval for refunds over the auto-approve threshold."""
        if skill_name != "process_refund":
            return {"requires_approval": False}

        amount = float(inputs.get("amount", 0))
        if amount > MAX_REFUND_NO_APPROVAL:
            approval_request = {
                "ticket_id": ticket_id,
                "skill": skill_name,
                "amount": amount,
                "status": "pending",
            }
            self._pending_approvals.append(approval_request)
            event = GuardrailEvent(
                guardrail_type="governance",
                trigger="high_value_action",
                severity="medium",
                original_text=f"Refund ${amount:.2f} for ticket {ticket_id}",
                action_taken="approval_required",
                ticket_id=ticket_id,
            )
            self._events.append(event)
            return {"requires_approval": True, "amount": amount, "threshold": MAX_REFUND_NO_APPROVAL}

        return {"requires_approval": False}

    def approve(self, ticket_id: str) -> bool:
        for req in self._pending_approvals:
            if req["ticket_id"] == ticket_id and req["status"] == "pending":
                req["status"] = "approved"
                return True
        return False

    def get_events(self) -> list[GuardrailEvent]:
        return list(self._events)

    def pending_approvals(self) -> list[dict[str, Any]]:
        return [r for r in self._pending_approvals if r["status"] == "pending"]
