"""Unit tests for Pydantic model properties and logic."""

from __future__ import annotations

import uuid

import pytest

from memory.models import (
    EvalMetrics, EvalReport, OutcomeType,
    Ticket, TicketCategory, TicketPriority, TicketStatus,
    Customer, Order, Plan, PlanStep, Trajectory, SharedTicketState,
    AgentRole, AgentStep, ToolCall, DelegationContract, DelegationResult,
    GuardrailEvent,
)


class TestEvalReport:
    def _make_metrics(self, plan_quality=0.8, tool_correctness=0.9,
                      task_completion=True, safety=1.0, latency=200.0,
                      outcome=OutcomeType.RESOLVED) -> EvalMetrics:
        return EvalMetrics(
            scenario_id="s1",
            ticket_id=str(uuid.uuid4()),
            plan_quality=plan_quality,
            tool_correctness=tool_correctness,
            task_completion=task_completion,
            step_efficiency=0.9,
            latency_ms=latency,
            safety_score=safety,
            outcome=outcome,
        )

    def test_empty_report_defaults(self):
        report = EvalReport()
        assert report.avg_plan_quality == 0.0
        assert report.avg_tool_correctness == 0.0
        assert report.task_completion_rate == 0.0
        assert report.avg_safety_score == 1.0
        assert report.avg_latency_ms == 0.0

    def test_single_result_averages(self):
        report = EvalReport()
        report.scenario_results.append(self._make_metrics(plan_quality=0.6, tool_correctness=0.8))
        assert report.avg_plan_quality == pytest.approx(0.6)
        assert report.avg_tool_correctness == pytest.approx(0.8)
        assert report.task_completion_rate == pytest.approx(1.0)

    def test_multiple_results_averaged(self):
        report = EvalReport()
        report.scenario_results.append(self._make_metrics(plan_quality=0.8, task_completion=True))
        report.scenario_results.append(self._make_metrics(plan_quality=0.4, task_completion=False))
        assert report.avg_plan_quality == pytest.approx(0.6)
        assert report.task_completion_rate == pytest.approx(0.5)

    def test_safety_score_averaged(self):
        report = EvalReport()
        report.scenario_results.append(self._make_metrics(safety=1.0))
        report.scenario_results.append(self._make_metrics(safety=0.0))
        assert report.avg_safety_score == pytest.approx(0.5)

    def test_latency_averaged(self):
        report = EvalReport()
        report.scenario_results.append(self._make_metrics(latency=100.0))
        report.scenario_results.append(self._make_metrics(latency=300.0))
        assert report.avg_latency_ms == pytest.approx(200.0)


class TestModelInstantiation:
    def test_ticket_defaults(self):
        t = Ticket(
            customer_id="c1",
            category=TicketCategory.BILLING_DISPUTE,
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            subject="Test",
            body="Test body",
        )
        assert t.ticket_id is not None
        assert t.status == TicketStatus.OPEN

    def test_customer_defaults(self):
        c = Customer(name="Bob", email="bob@example.com")
        assert c.tier == "standard"
        assert c.customer_id is not None

    def test_plan_step_defaults(self):
        ps = PlanStep(skill_name="lookup_order")
        assert ps.inputs == {}
        assert ps.depends_on == []

    def test_delegation_contract(self):
        dc = DelegationContract(
            task_type="billing",
            delegating_agent="planner-1",
            target_agent_role=AgentRole.BILLING,
            shared_memory_ref="ticket-abc",
        )
        assert dc.timeout_s == 30.0
        assert dc.fallback_action == "escalate"

    def test_delegation_result_success(self):
        dr = DelegationResult(contract_id="c1", success=True, outputs={"refund_amount": 49.99})
        assert dr.success is True
        assert dr.error is None

    def test_guardrail_event_defaults(self):
        ge = GuardrailEvent(
            guardrail_type="input",
            trigger="pii",
            original_text="my SSN is 123-45-6789",
            action_taken="anonymized",
        )
        assert ge.severity == "medium"
        assert ge.event_id is not None

    def test_shared_ticket_state_version_starts_at_zero(self):
        t = Ticket(
            customer_id="c1",
            category=TicketCategory.BILLING_DISPUTE,
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            subject="S",
            body="B",
        )
        state = SharedTicketState(ticket_id=t.ticket_id, ticket=t)
        assert state.version == 0
        assert state.assigned_agents == []
        assert state.notes == []
