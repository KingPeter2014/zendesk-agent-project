"""Input guardrails: PII detection, prompt injection, toxic content."""

from __future__ import annotations

import re
from typing import Any

from memory.models import GuardrailEvent

# Prompt injection patterns
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(previous|all|prior)\s+instructions?",
        r"disregard\s+(safety|guidelines|policies?)",
        r"you\s+are\s+now\s+a?\s+free\s+(ai|assistant)",
        r"SYSTEM\s*:\s*",
        r"jailbreak",
        r"pretend\s+(you\s+are|to\s+be)\s+an?\s+(evil|unrestricted)",
        r"act\s+as\s+(if\s+you\s+have\s+)?no\s+(restrictions?|limits?|rules?)",
        r"refund\s+all\s+(orders?|accounts?|users?)",
        r"delete\s+(all|every)\s+(record|data|order|customer)",
        r"dump\s+(all|the)\s+(database|data|records?)",
    ]
]

# PII patterns (simplified for demo; Presidio handles production cases)
_PII_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")),
    ("email_in_body", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("date_of_birth", re.compile(r"\bD\.?O\.?B\.?\s*:?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", re.IGNORECASE)),
]


class InputGuardrails:
    """
    Screens incoming ticket text before the agent processes it.
    Uses regex-based detection; extend with Presidio for production.
    """

    def __init__(self) -> None:
        self._events: list[GuardrailEvent] = []

    def check_input(self, text: str, ticket_id: str | None = None, agent_id: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "blocked": False,
            "pii_detected": False,
            "pii_types": [],
            "injection_detected": False,
            "sanitised_text": text,
            "events": [],
        }

        # --- Prompt injection check ---
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                event = GuardrailEvent(
                    guardrail_type="input",
                    trigger="prompt_injection",
                    severity="critical",
                    original_text=text[:200],
                    action_taken="blocked",
                    ticket_id=ticket_id,
                    agent_id=agent_id,
                )
                self._events.append(event)
                result["blocked"] = True
                result["injection_detected"] = True
                result["events"].append(event.model_dump(mode="json"))
                return result  # Hard block — no further processing

        # --- PII detection ---
        sanitised = text
        for pii_type, pattern in _PII_PATTERNS:
            if pattern.search(text):
                result["pii_detected"] = True
                result["pii_types"].append(pii_type)
                sanitised = pattern.sub(f"[{pii_type.upper()}_REDACTED]", sanitised)
                event = GuardrailEvent.pii_redacted("input", text, ticket_id, agent_id)
                self._events.append(event)
                result["events"].append(event.model_dump(mode="json"))

        result["sanitised_text"] = sanitised
        return result

    def get_events(self) -> list[GuardrailEvent]:
        return list(self._events)

    def event_count(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._events:
            counts[e.trigger] = counts.get(e.trigger, 0) + 1
        return counts
