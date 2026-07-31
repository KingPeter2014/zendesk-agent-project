"""Unit tests for skill registry and built-in skills."""

from __future__ import annotations

import pytest

from skills.builtin.check_policy import check_policy
from skills.builtin.escalate_ticket import escalate_ticket
from skills.builtin.process_refund import process_refund
from skills.builtin.send_notification import send_notification
from skills.registry import SkillMetadata, SkillRegistry


class TestSkillRegistry:
    def test_register_and_get(self, registry):
        entry = registry.get("lookup_order")
        assert entry is not None
        meta, fn = entry
        assert meta.name == "lookup_order"

    def test_list_available(self, registry):
        skills = registry.list_available()
        names = [s.name for s in skills]
        assert "lookup_order" in names
        assert "process_refund" in names

    def test_gated_skill_not_listed(self, registry):
        from skills.builtin.check_policy import check_policy as cp
        gated_meta = SkillMetadata(
            name="experimental_skill",
            description="Not promoted yet",
            gating_enabled=True,
            is_promoted=False,
        )
        registry.register(gated_meta, cp)
        names = [s.name for s in registry.list_available()]
        assert "experimental_skill" not in names

    def test_promotion(self, registry):
        # Register a gated skill and simulate enough successful invocations
        from skills.builtin.check_policy import check_policy as cp
        meta = SkillMetadata(name="promotable", description="test", gating_enabled=True, is_promoted=False)
        registry.register(meta, cp)
        for _ in range(10):
            registry.record_invocation("promotable", success=True)
        assert registry.get("promotable")[0].is_promoted is True

    def test_success_rate(self, registry):
        registry.record_invocation("lookup_order", success=True)
        registry.record_invocation("lookup_order", success=False)
        meta, _ = registry.get("lookup_order")
        assert meta.success_rate == 0.5


class TestBuiltinSkills:
    def test_process_refund_success(self):
        result = process_refund(order_id="abc123", amount=49.99)
        assert result["success"] is True
        assert result["refund_amount"] == 49.99

    def test_process_refund_no_order_id(self):
        result = process_refund(order_id="", amount=10.0)
        assert result["success"] is False

    def test_process_refund_zero_amount(self):
        result = process_refund(order_id="abc", amount=0.0)
        assert result["success"] is False

    def test_check_policy_refund(self):
        result = check_policy(query="How long does a refund take?")
        assert result["policies_found"] > 0
        assert any("refund" in p["text"].lower() for p in result["policies"])

    def test_check_policy_returns_all_when_no_match(self):
        result = check_policy(query="something completely unrelated")
        assert result["policies_found"] > 0

    def test_escalate_ticket(self):
        result = escalate_ticket(ticket_id="t-001", reason="VIP complaint", priority="critical", queue="vip")
        assert result["success"] is True
        assert "vip" in result["escalated_to"]

    def test_send_notification_invalid_channel(self):
        result = send_notification(customer_id="c-1", message="Hello", channel="fax")
        assert result["success"] is False
