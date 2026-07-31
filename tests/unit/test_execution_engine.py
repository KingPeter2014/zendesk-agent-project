"""Unit tests for ExecutionEngine."""

from __future__ import annotations

import uuid

import pytest

from memory.models import AgentRole, OutcomeType, Plan, PlanStep, Ticket, TicketCategory, TicketPriority, TicketStatus
from memory.working_memory import WorkingMemory
from skills.builtin.register import build_default_registry
from skills.execution_engine import ExecutionEngine


def _make_plan(ticket_id: str, steps: list[dict]) -> Plan:
    return Plan(
        ticket_id=ticket_id,
        objective="Test objective",
        steps=[PlanStep(**s) for s in steps],
    )


@pytest.fixture
def engine(registry):
    return ExecutionEngine(registry, agent_id="test-engine", agent_role=AgentRole.BILLING)


@pytest.fixture
def ticket() -> Ticket:
    return Ticket(
        ticket_id=str(uuid.uuid4()),
        customer_id=str(uuid.uuid4()),
        category=TicketCategory.BILLING_DISPUTE,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        subject="Test",
        body="Test body",
    )


class TestExecutionEngine:
    def test_executes_single_skill(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [
            {"skill_name": "check_policy", "inputs": {"query": "return policy"}}
        ])
        traj = engine.execute(plan, wm)
        assert len(traj.steps) == 1
        assert traj.steps[0].tool_calls[0].tool_name == "check_policy"
        assert traj.outcome == OutcomeType.RESOLVED

    def test_executes_multiple_skills_in_order(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [
            {"skill_name": "check_policy", "inputs": {"query": "refund"}},
            {"skill_name": "send_notification", "inputs": {
                "customer_id": ticket.customer_id, "message": "Done", "channel": "email"
            }},
        ])
        traj = engine.execute(plan, wm)
        tool_names = [tc.tool_name for s in traj.steps for tc in s.tool_calls]
        assert tool_names == ["check_policy", "send_notification"]

    def test_unknown_skill_sets_error(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [
            {"skill_name": "nonexistent_skill", "inputs": {}}
        ])
        traj = engine.execute(plan, wm)
        assert traj.steps[0].tool_calls[0].error is not None
        assert "not found" in traj.steps[0].tool_calls[0].error

    def test_failed_skill_sets_failed_outcome(self, engine, ticket, registry):
        def always_fails(**kwargs):
            raise RuntimeError("deliberate failure")
        from skills.registry import SkillMetadata
        registry.register(SkillMetadata(name="failing_skill", description="always fails"), always_fails)

        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [{"skill_name": "failing_skill", "inputs": {}}])
        traj = engine.execute(plan, wm)
        assert traj.outcome == OutcomeType.FAILED
        assert traj.steps[0].tool_calls[0].error is not None

    def test_latency_recorded(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [{"skill_name": "check_policy", "inputs": {"query": "warranty"}}])
        traj = engine.execute(plan, wm)
        assert traj.total_latency_ms >= 0
        assert traj.steps[0].tool_calls[0].latency_ms >= 0

    def test_working_memory_updated(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [{"skill_name": "check_policy", "inputs": {"query": "exchange"}}])
        engine.execute(plan, wm)
        assert "check_policy" in wm.tool_results
        assert len(wm.tool_call_log) == 1

    def test_empty_plan_resolves(self, engine, ticket):
        wm = WorkingMemory(ticket.ticket_id, "agent-1")
        plan = _make_plan(ticket.ticket_id, [])
        traj = engine.execute(plan, wm)
        assert traj.outcome == OutcomeType.RESOLVED
        assert len(traj.steps) == 0
