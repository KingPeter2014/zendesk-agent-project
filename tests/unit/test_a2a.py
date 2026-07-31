"""Unit tests for A2A protocol and capability registry."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from a2a.capability_registry import AgentCapability, CapabilityRegistry
from a2a.protocol import A2AProtocol
from memory.models import AgentRole, DelegationContract, DelegationResult


class TestCapabilityRegistry:
    def test_register_and_find(self):
        reg = CapabilityRegistry()
        cap = AgentCapability(
            agent_id="billing-01", agent_role="billing",
            task_types=["billing", "refund"],
            description="Handles billing",
        )
        reg.register(cap)
        found = reg.find("refund")
        assert found is not None
        assert found.agent_role == "billing"

    def test_find_returns_none_for_unknown(self):
        reg = CapabilityRegistry()
        assert reg.find("unknown_task") is None

    def test_find_all_returns_multiple(self):
        reg = CapabilityRegistry()
        reg.register(AgentCapability("a1", "billing", ["billing"], ""))
        reg.register(AgentCapability("a2", "billing_specialist", ["billing", "vip"], ""))
        found = reg.find_all("billing")
        assert len(found) == 2

    def test_list_all(self):
        reg = CapabilityRegistry()
        reg.register(AgentCapability("a1", "billing", ["billing"], ""))
        reg.register(AgentCapability("a2", "policy", ["policy"], ""))
        assert len(reg.list_all()) == 2

    def test_last_registration_wins_for_same_agent_id(self):
        reg = CapabilityRegistry()
        reg.register(AgentCapability("a1", "billing", ["billing"], "first"))
        reg.register(AgentCapability("a1", "billing", ["billing", "refund"], "second"))
        assert len(reg.list_all()) == 1
        assert "refund" in reg.list_all()[0].task_types


class TestA2AProtocol:
    def _make_protocol(self, handler_result: DelegationResult | None = None):
        cap_reg = CapabilityRegistry()
        if handler_result is not None:
            handler = MagicMock(return_value=handler_result)
        else:
            handler = MagicMock(return_value=DelegationResult(
                contract_id="c1", success=True, outputs={"refund_amount": 49.99}
            ))
        cap_reg.register(AgentCapability(
            agent_id="billing-01", agent_role="billing",
            task_types=["billing"],
            description="Billing",
            handler=handler,
        ))
        shared_mem = MagicMock()
        shared_mem.get.return_value = None
        protocol = A2AProtocol(cap_reg, shared_mem)
        return protocol, handler

    def test_successful_delegation(self):
        protocol, handler = self._make_protocol()
        result = protocol.delegate(
            task_type="billing",
            delegating_agent="planner",
            ticket_id=str(uuid.uuid4()),
            inputs={"order_id": "abc", "amount": 49.99},
        )
        assert result.success is True
        handler.assert_called_once()

    def test_unknown_task_type_returns_failure(self):
        protocol, _ = self._make_protocol()
        result = protocol.delegate(
            task_type="nonexistent",
            delegating_agent="planner",
            ticket_id=str(uuid.uuid4()),
            inputs={},
        )
        assert result.success is False
        assert "No agent registered" in result.error

    def test_handler_exception_returns_failure(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register(AgentCapability(
            agent_id="bad-agent", agent_role="billing",
            task_types=["billing"],
            description="Raises",
            handler=MagicMock(side_effect=RuntimeError("agent crashed")),
        ))
        shared_mem = MagicMock()
        shared_mem.get.return_value = None
        protocol = A2AProtocol(cap_reg, shared_mem)
        result = protocol.delegate("billing", "planner", "t1", {})
        assert result.success is False
        assert "agent crashed" in result.error

    def test_no_handler_returns_failure(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register(AgentCapability(
            agent_id="no-handler", agent_role="billing",
            task_types=["billing"],
            description="No handler",
            handler=None,
        ))
        shared_mem = MagicMock()
        protocol = A2AProtocol(cap_reg, shared_mem)
        result = protocol.delegate("billing", "planner", "t1", {})
        assert result.success is False
