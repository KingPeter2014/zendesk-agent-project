"""Shared fixtures for all tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from memory.models import (
    Customer, Order, Ticket, TicketCategory, TicketPriority, TicketStatus,
)
from memory.per_agent_memory import PerAgentMemory
from memory.working_memory import WorkingMemory
from skills.builtin.register import build_default_registry


@pytest.fixture
def sample_ticket() -> Ticket:
    return Ticket(
        ticket_id=str(uuid.uuid4()),
        customer_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        category=TicketCategory.BILLING_DISPUTE,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        subject="Refund request",
        body="I was charged twice for order #abc123. Please refund $49.99.",
    )


@pytest.fixture
def sample_customer() -> Customer:
    return Customer(name="Alice Smith", email="alice@example.com", tier="premium")


@pytest.fixture
def registry():
    return build_default_registry()


@pytest.fixture
def per_agent_memory(tmp_path):
    return PerAgentMemory(db_path=tmp_path / "test_memory.db")


@pytest.fixture
def working_memory(sample_ticket) -> WorkingMemory:
    return WorkingMemory(ticket_id=sample_ticket.ticket_id, agent_id="test-agent")
