"""Base class for all Zendesk agents."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from memory.models import (
    AgentRole, DelegationContract, DelegationResult, OutcomeType, Ticket, Trajectory,
)
from memory.per_agent_memory import PerAgentMemory
from memory.shared_memory import SharedTicketMemory
from memory.working_memory import WorkingMemory
from skills.registry import SkillRegistry


class BaseAgent(ABC):

    def __init__(
        self,
        role: AgentRole,
        registry: SkillRegistry,
        shared_memory: SharedTicketMemory,
        per_agent_memory: PerAgentMemory,
        agent_id: str | None = None,
    ) -> None:
        self.role = role
        self.agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:8]}"
        self.registry = registry
        self.shared_memory = shared_memory
        self.per_agent_memory = per_agent_memory

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        """Process a ticket and return a trajectory."""

    # ------------------------------------------------------------------
    # A2A handler interface (optional)
    # ------------------------------------------------------------------

    def handle_delegation(self, contract: DelegationContract) -> DelegationResult:
        """Run this agent's `handle()` against a delegated ticket and report the outcome.

        Override `_delegation_succeeded` to customize what counts as success;
        override this method entirely for agents that don't accept delegated tasks.
        """
        state = self.shared_memory.get(contract.shared_memory_ref)
        if state is None:
            return DelegationResult(contract_id=contract.contract_id, success=False, error="Ticket state not found")

        trajectory = self.handle(state.ticket, contract.inputs)
        outputs: dict[str, Any] = {}
        for step in trajectory.steps:
            for tc in step.tool_calls:
                if tc.output:
                    outputs[tc.tool_name] = tc.output

        return DelegationResult(
            contract_id=contract.contract_id,
            success=self._delegation_succeeded(trajectory),
            outputs=outputs,
        )

    def _delegation_succeeded(self, trajectory: Trajectory) -> bool:
        """Whether a delegated task's trajectory counts as a success. Override per agent."""
        return trajectory.outcome == OutcomeType.RESOLVED

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _make_working_memory(self, ticket_id: str) -> WorkingMemory:
        return WorkingMemory(ticket_id=ticket_id, agent_id=self.agent_id)

    def _log_note(self, ticket_id: str, note: str) -> None:
        state = self.shared_memory.get(ticket_id)
        if state is None:
            return
        self.shared_memory.update_with_retry(
            ticket_id, {"notes": state.notes + [f"[{self.role.value}] {note}"]}
        )
