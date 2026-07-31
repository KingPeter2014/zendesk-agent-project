"""Unit tests for skill pruning and context summarisation."""

from __future__ import annotations

from skills.builtin.check_policy import check_policy
from skills.registry import SkillMetadata, SkillRegistry
from memory.working_memory import WorkingMemory
from memory.models import Plan, ToolCall


def test_prune_unused_gated_skill():
    registry = SkillRegistry()
    meta = SkillMetadata(name="unused_skill", description="Never called", gating_enabled=True, is_promoted=False)
    registry.register(meta, check_policy)
    pruned = registry.prune_unused(protect=[])
    assert "unused_skill" in pruned
    assert registry.get("unused_skill") is None


def test_prune_failing_skill():
    registry = SkillRegistry()
    meta = SkillMetadata(name="bad_skill", description="Always fails", gating_enabled=True, is_promoted=True)
    registry.register(meta, check_policy)
    for _ in range(10):
        registry.record_invocation("bad_skill", success=False)
    pruned = registry.prune_unused(min_invocations=5, min_success_rate=0.5)
    assert "bad_skill" in pruned


def test_builtin_protected_from_pruning():
    from skills.builtin.register import build_default_registry
    registry = build_default_registry()
    # Mark a builtin as gated to simulate danger
    meta, fn = registry.get("lookup_order")
    meta.gating_enabled = True
    # Still protected by name
    pruned = registry.prune_unused(protect=["lookup_order"])
    assert "lookup_order" not in pruned


def test_summarise_context():
    wm = WorkingMemory(ticket_id="ticket-abc123", agent_id="agent-xyz")
    plan = Plan(ticket_id="ticket-abc123", objective="Resolve billing issue")
    wm.set_plan(plan)
    tc = ToolCall(tool_name="lookup_order", inputs={}, output={"found": True})
    wm.record_tool_call(tc, result_key="lookup_order")
    wm.add_reasoning("Checking order before refund")
    summary = wm.summarise_context()
    assert "ticket=ticket-a" in summary
    assert "lookup_order" in summary
    assert len(summary) <= 500
