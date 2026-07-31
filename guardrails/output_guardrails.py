"""Output guardrails: PII scrubbing, hallucination detection, policy adherence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from memory.models import GuardrailEvent

_PII_OUTPUT_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b")),
    ("credit_card", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
]


class OutputGuardrails:

    def __init__(self, orders_path: str = "data/orders.json") -> None:
        self._orders_path = Path(orders_path)
        self._events: list[GuardrailEvent] = []

    def _load_order_ids(self) -> set[str]:
        if not self._orders_path.exists():
            return set()
        orders = json.loads(self._orders_path.read_text())
        return {o["order_id"] for o in orders}

    def scrub_output(self, text: str, ticket_id: str | None = None) -> dict[str, Any]:
        result = {"scrubbed": False, "text": text, "events": []}
        scrubbed = text
        for pii_type, pattern in _PII_OUTPUT_PATTERNS:
            if pattern.search(scrubbed):
                scrubbed = pattern.sub(f"[{pii_type.upper()}_REDACTED]", scrubbed)
                event = GuardrailEvent.pii_redacted("output", text, ticket_id)
                self._events.append(event)
                result["scrubbed"] = True
                result["events"].append(event.model_dump(mode="json"))

        result["text"] = scrubbed
        return result

    def check_hallucination(self, claimed_order_id: str, ticket_id: str | None = None) -> dict[str, Any]:
        """Verify a claimed order ID actually exists in the synthetic database."""
        valid_ids = self._load_order_ids()
        if valid_ids and claimed_order_id not in valid_ids:
            event = GuardrailEvent(
                guardrail_type="output",
                trigger="hallucination",
                severity="medium",
                original_text=f"claimed_order_id={claimed_order_id}",
                action_taken="flagged",
                ticket_id=ticket_id,
            )
            self._events.append(event)
            return {"hallucination_detected": True, "order_id": claimed_order_id}
        return {"hallucination_detected": False}

    def get_events(self) -> list[GuardrailEvent]:
        return list(self._events)
