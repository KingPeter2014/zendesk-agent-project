"""Integration tests for agent pipelines (no Redis, no Ollama required)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from memory.models import (
    AgentRole, OutcomeType, SharedTicketState, Ticket,
    TicketCategory, TicketPriority, TicketStatus,
)
from memory.per_agent_memory import PerAgentMemory
from memory.shared_memory import SharedTicketMemory
from skills.builtin.register import build_default_registry
from agents.billing_agent import BillingAgent
from agents.policy_agent import PolicyAgent
from agents.escalation_agent import EscalationAgent


def _make_ticket(category: TicketCategory, priority: TicketPriority = TicketPriority.MEDIUM) -> Ticket:
    return Ticket(
        ticket_id=str(uuid.uuid4()),
        customer_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        category=category,
        priority=priority,
        status=TicketStatus.OPEN,
        subject="Test ticket",
        body="Test body for integration test.",
    )


@pytest.fixture
def mock_shared_memory():
    """Mock SharedTicketMemory for tests that don't need Redis."""
    mock = MagicMock(spec=SharedTicketMemory)
    mock.get.return_value = None
    mock.update_with_retry.return_value = None
    return mock


@pytest.fixture
def agent_kwargs(mock_shared_memory, tmp_path):
    return dict(
        registry=build_default_registry(),
        shared_memory=mock_shared_memory,
        per_agent_memory=PerAgentMemory(db_path=tmp_path / "agents.db"),
    )


class TestBillingAgent:
    def test_billing_agent_resolves(self, agent_kwargs):
        agent = BillingAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.BILLING_DISPUTE)
        trajectory = agent.handle(ticket, context={"order_id": ticket.order_id, "amount": 49.99})
        assert trajectory.ticket_id == ticket.ticket_id
        assert len(trajectory.steps) > 0

    def test_billing_agent_uses_correct_skills(self, agent_kwargs):
        agent = BillingAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.BILLING_DISPUTE)
        trajectory = agent.handle(ticket, context={"order_id": "abc123", "amount": 29.99})
        tool_names = [tc.tool_name for step in trajectory.steps for tc in step.tool_calls]
        assert "process_refund" in tool_names

    def test_billing_handles_delegation_contract(self, agent_kwargs):
        from memory.models import DelegationContract
        agent = BillingAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.BILLING_DISPUTE)
        state = SharedTicketState(ticket_id=ticket.ticket_id, ticket=ticket)
        agent_kwargs["shared_memory"].get.return_value = state

        contract = DelegationContract(
            task_type="billing",
            delegating_agent="meta_planner",
            target_agent_role=AgentRole.BILLING,
            shared_memory_ref=ticket.ticket_id,
            inputs={"order_id": ticket.order_id, "amount": 50.0},
        )
        result = agent.handle_delegation(contract)
        assert result.contract_id == contract.contract_id


class TestPolicyAgent:
    def test_policy_agent_resolves(self, agent_kwargs):
        agent = PolicyAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.POLICY_QUESTION)
        trajectory = agent.handle(ticket, context={"policy_query": "What is the return policy?"})
        tool_names = [tc.tool_name for step in trajectory.steps for tc in step.tool_calls]
        assert "check_policy" in tool_names


class TestEscalationAgent:
    def test_escalation_outcome(self, agent_kwargs):
        agent = EscalationAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.VIP_ESCALATION, TicketPriority.CRITICAL)
        trajectory = agent.handle(ticket, context={"reason": "VIP complaint", "queue": "vip"})
        assert trajectory.outcome == OutcomeType.ESCALATED

    def test_escalation_uses_correct_skills(self, agent_kwargs):
        agent = EscalationAgent(**agent_kwargs)
        ticket = _make_ticket(TicketCategory.VIP_ESCALATION, TicketPriority.HIGH)
        trajectory = agent.handle(ticket)
        tool_names = [tc.tool_name for step in trajectory.steps for tc in step.tool_calls]
        assert "escalate_ticket" in tool_names


class TestEvaluationMetrics:
    def test_tool_correctness_perfect(self):
        from evaluation.metrics import compute_tool_correctness
        from memory.models import AgentStep, ToolCall, Trajectory

        step = AgentStep(agent_id="a", agent_role=AgentRole.BILLING, action="execute:lookup_order")
        step.tool_calls = [ToolCall(tool_name="lookup_order", inputs={})]
        traj = Trajectory(ticket_id="t", agent_id="a", steps=[step], outcome=OutcomeType.RESOLVED)
        assert compute_tool_correctness(traj, ["lookup_order"]) == 1.0

    def test_tool_correctness_partial(self):
        from evaluation.metrics import compute_tool_correctness
        from memory.models import AgentStep, ToolCall, Trajectory

        step = AgentStep(agent_id="a", agent_role=AgentRole.BILLING, action="execute:lookup_order")
        step.tool_calls = [ToolCall(tool_name="lookup_order", inputs={})]
        traj = Trajectory(ticket_id="t", agent_id="a", steps=[step], outcome=OutcomeType.RESOLVED)
        # Expected 2 tools, only 1 used
        score = compute_tool_correctness(traj, ["lookup_order", "process_refund"])
        assert score == 0.5
