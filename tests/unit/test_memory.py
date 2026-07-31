"""Unit tests for memory layer."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from memory.models import Ticket, TicketCategory, TicketPriority, TicketStatus, SharedTicketState
from memory.per_agent_memory import PerAgentMemory
from memory.working_memory import WorkingMemory
from memory.models import Plan, PlanStep, ToolCall


class TestWorkingMemory:
    def test_set_plan(self, working_memory, sample_ticket):
        plan = Plan(ticket_id=sample_ticket.ticket_id, objective="Test objective")
        working_memory.set_plan(plan)
        assert working_memory.plan is not None
        assert working_memory.plan.objective == "Test objective"

    def test_record_tool_call(self, working_memory):
        tc = ToolCall(tool_name="lookup_order", inputs={"order_id": "abc"}, output={"found": True})
        working_memory.record_tool_call(tc, result_key="lookup_order")
        assert len(working_memory.tool_call_log) == 1
        assert "lookup_order" in working_memory.tool_results

    def test_clarification(self, working_memory):
        working_memory.request_clarification("What is your order number?")
        assert working_memory.clarification_needed is True
        assert "order number" in working_memory.clarification_question

    def test_snapshot(self, working_memory, sample_ticket):
        snap = working_memory.snapshot()
        assert snap["ticket_id"] == sample_ticket.ticket_id
        assert snap["clarification_needed"] is False


class TestPerAgentMemory:
    def test_set_get(self, per_agent_memory):
        per_agent_memory.set("agent-1", "ticket-1", "draft", {"text": "hello"})
        val = per_agent_memory.get("agent-1", "ticket-1", "draft")
        assert val == {"text": "hello"}

    def test_get_missing_returns_default(self, per_agent_memory):
        val = per_agent_memory.get("agent-x", "ticket-x", "key", default="fallback")
        assert val == "fallback"

    def test_overwrite(self, per_agent_memory):
        per_agent_memory.set("a", "t", "k", 1)
        per_agent_memory.set("a", "t", "k", 2)
        assert per_agent_memory.get("a", "t", "k") == 2

    def test_get_all(self, per_agent_memory):
        per_agent_memory.set("a", "t", "x", 10)
        per_agent_memory.set("a", "t", "y", 20)
        all_vals = per_agent_memory.get_all("a", "t")
        assert all_vals == {"x": 10, "y": 20}

    def test_clear_ticket(self, per_agent_memory):
        per_agent_memory.set("a", "t", "k", 1)
        per_agent_memory.clear_ticket("a", "t")
        assert per_agent_memory.get("a", "t", "k") is None


class TestSharedMemoryOptimisticLocking:
    """Test optimistic locking without a real Redis — uses fakeredis if available."""

    def test_version_conflict_error_raised(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")

        from memory.shared_memory import SharedTicketMemory, VersionConflictError

        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
            ticket = Ticket(
                ticket_id="t-conflict",
                customer_id="c-1",
                category=TicketCategory.BILLING_DISPUTE,
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.OPEN,
                subject="Test",
                body="Test body",
            )
            state = SharedTicketState(ticket_id="t-conflict", ticket=ticket)
            mem.create(state)

            # First update succeeds
            mem.update("t-conflict", {"active_agent": "agent-1"}, expected_version=0)

            # Second update with stale version raises
            with pytest.raises(VersionConflictError):
                mem.update("t-conflict", {"active_agent": "agent-2"}, expected_version=0)


def _make_fake_mem():
    """Return (SharedTicketMemory, FakeRedis) using fakeredis, skipping if not available."""
    try:
        import fakeredis
    except ImportError:
        pytest.skip("fakeredis not installed")
    from memory.shared_memory import SharedTicketMemory
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    with patch("memory.shared_memory.redis.Redis", return_value=fake_redis):
        mem = SharedTicketMemory()
    return mem, fake_redis


def _make_ticket_state(ticket_id: str = "t-test") -> tuple:
    ticket = Ticket(
        ticket_id=ticket_id,
        customer_id="c-1",
        category=TicketCategory.BILLING_DISPUTE,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        subject="Test",
        body="Test body",
    )
    state = SharedTicketState(ticket_id=ticket_id, ticket=ticket)
    return ticket, state


class TestSharedMemoryCRUD:
    def test_get_returns_none_for_missing(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        result = mem.get("nonexistent-ticket")
        assert result is None

    def test_get_returns_state_when_exists(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        _, state = _make_ticket_state("t-get")
        mem.create(state)
        fetched = mem.get("t-get")
        assert fetched is not None
        assert fetched.ticket_id == "t-get"

    def test_exists_false_for_missing(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        assert mem.exists("no-such-ticket") is False

    def test_exists_true_after_create(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        _, state = _make_ticket_state("t-exists")
        mem.create(state)
        assert mem.exists("t-exists") is True

    def test_create_duplicate_raises(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        _, state = _make_ticket_state("t-dup")
        mem.create(state)
        with pytest.raises(ValueError, match="already exists"):
            mem.create(state)

    def test_delete_removes_ticket(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        _, state = _make_ticket_state("t-delete")
        mem.create(state)
        mem.delete("t-delete")
        assert mem.exists("t-delete") is False

    def test_update_missing_ticket_raises_keyerror(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        with pytest.raises(KeyError):
            mem.update("no-such-ticket", {"active_agent": "x"}, expected_version=0)

    def test_update_with_retry_succeeds(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        _, state = _make_ticket_state("t-retry")
        mem.create(state)
        updated = mem.update_with_retry("t-retry", {"active_agent": "agent-x"})
        assert updated.active_agent == "agent-x"

    def test_update_with_retry_missing_raises_keyerror(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        with patch("memory.shared_memory.redis.Redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            mem = SharedTicketMemory()
        with pytest.raises(KeyError):
            mem.update_with_retry("no-ticket", {"active_agent": "x"})

    def test_init_from_ticket_creates_new(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        ticket, _ = _make_ticket_state("t-init")
        with patch("memory.shared_memory.redis.Redis", return_value=fake_redis):
            mem, state = SharedTicketMemory.init_from_ticket(ticket)
        assert state.ticket_id == "t-init"

    def test_init_from_ticket_returns_existing(self):
        try:
            import fakeredis
        except ImportError:
            pytest.skip("fakeredis not installed")
        from memory.shared_memory import SharedTicketMemory
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        ticket, initial_state = _make_ticket_state("t-init2")
        with patch("memory.shared_memory.redis.Redis", return_value=fake_redis):
            mem1, _ = SharedTicketMemory.init_from_ticket(ticket)
            # second call should return existing state
            mem2, state2 = SharedTicketMemory.init_from_ticket(ticket)
        assert state2.ticket_id == "t-init2"
