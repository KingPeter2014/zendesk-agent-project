"""Unit tests for output guardrails and governance."""

from __future__ import annotations

import pytest

from guardrails.output_guardrails import OutputGuardrails


class TestOutputGuardrails:
    @pytest.fixture
    def og(self, tmp_path):
        # Create a minimal orders file so hallucination check works
        import json
        orders_path = tmp_path / "orders.json"
        orders_path.write_text(json.dumps([
            {"order_id": "real-order-001"},
            {"order_id": "real-order-002"},
        ]))
        return OutputGuardrails(orders_path=str(orders_path))

    def test_scrubs_email(self, og):
        result = og.scrub_output("Reply to user@company.com for details")
        assert result["scrubbed"] is True
        assert "user@company.com" not in result["text"]
        assert "EMAIL" in result["text"]

    def test_scrubs_credit_card(self, og):
        result = og.scrub_output("Customer card 4111111111111111 was charged")
        assert result["scrubbed"] is True
        assert "4111" not in result["text"]

    def test_clean_text_unchanged(self, og):
        text = "Your refund of $49.99 will arrive in 5 business days."
        result = og.scrub_output(text)
        assert result["scrubbed"] is False
        assert result["text"] == text

    def test_hallucination_detected_for_unknown_order(self, og):
        result = og.check_hallucination("fake-order-xyz")
        assert result["hallucination_detected"] is True

    def test_hallucination_not_detected_for_real_order(self, og):
        result = og.check_hallucination("real-order-001")
        assert result["hallucination_detected"] is False

    def test_events_recorded_on_scrub(self, og):
        og.scrub_output("Contact test@example.com")
        events = og.get_events()
        assert len(events) >= 1
        assert events[0].trigger == "pii"

    def test_multiple_scrubs_accumulate_events(self, og):
        og.scrub_output("Email: a@b.com")
        og.scrub_output("Email: c@d.com")
        assert len(og.get_events()) == 2

    def test_no_orders_db_returns_no_hallucination(self, tmp_path):
        og_no_db = OutputGuardrails(orders_path=str(tmp_path / "missing.json"))
        result = og_no_db.check_hallucination("any-order-id")
        assert result["hallucination_detected"] is False
