"""A2A delegation protocol: create, dispatch, and receive task results."""

from __future__ import annotations

import time
from typing import Any

from opentelemetry import trace

from a2a.capability_registry import CapabilityRegistry
from memory.models import AgentRole, DelegationContract, DelegationResult, OutcomeType
from memory.shared_memory import SharedTicketMemory
from observability.tracing import get_tracer


class A2AProtocol:
    """
    Orchestrates agent-to-agent delegation.
    - Planner calls `delegate()` with a task_type and inputs.
    - The target agent is looked up via CapabilityRegistry.
    - The contract is passed to the handler; result written to shared memory.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        shared_memory: SharedTicketMemory,
    ) -> None:
        self._capabilities = capability_registry
        self._shared_memory = shared_memory

    def delegate(
        self,
        task_type: str,
        delegating_agent: str,
        ticket_id: str,
        inputs: dict[str, Any],
        expected_output_keys: list[str] | None = None,
        timeout_s: float = 30.0,
    ) -> DelegationResult:
        tracer = get_tracer()
        with tracer.start_as_current_span(f"a2a.delegate.{task_type}") as span:
            span.set_attribute("delegation.task_type", task_type)
            span.set_attribute("delegation.delegating_agent", delegating_agent)
            span.set_attribute("delegation.ticket_id", ticket_id)

            cap = self._capabilities.find(task_type)
            if cap is None:
                span.set_status(trace.StatusCode.ERROR, "no agent registered")
                return DelegationResult(
                    contract_id="",
                    success=False,
                    error=f"No agent registered for task_type='{task_type}'",
                )

            contract = DelegationContract(
                task_type=task_type,
                delegating_agent=delegating_agent,
                target_agent_role=AgentRole(cap.agent_role),
                shared_memory_ref=ticket_id,
                inputs=inputs,
                expected_output_keys=expected_output_keys or [],
                timeout_s=timeout_s,
            )
            span.set_attribute("delegation.target_agent_role", cap.agent_role)

            if cap.handler is None:
                span.set_status(trace.StatusCode.ERROR, "no handler registered")
                return DelegationResult(
                    contract_id=contract.contract_id,
                    success=False,
                    error=f"Agent '{cap.agent_id}' has no handler registered",
                )

            deadline = time.time() + timeout_s
            try:
                result: DelegationResult = cap.handler(contract)
                if time.time() > deadline:
                    span.set_status(trace.StatusCode.ERROR, "timed out")
                    return DelegationResult(
                        contract_id=contract.contract_id,
                        success=False,
                        error="Delegation timed out",
                    )
                # Write key outputs back to shared memory
                if result.success and result.outputs:
                    state = self._shared_memory.get(ticket_id)
                    if state is not None:
                        merged = {**state.tool_results, **result.outputs}
                        self._shared_memory.update_with_retry(
                            ticket_id, {"tool_results": merged}
                        )
                span.set_attribute("delegation.success", result.success)
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                return DelegationResult(
                    contract_id=contract.contract_id,
                    success=False,
                    error=str(exc),
                )
