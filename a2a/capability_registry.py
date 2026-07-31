"""Agent capability advertisement and discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent


@dataclass
class AgentCapability:
    agent_id: str
    agent_role: str
    task_types: list[str]
    description: str
    required_inputs: list[str] = field(default_factory=list)
    handler: Callable | None = field(default=None, repr=False)


class CapabilityRegistry:
    """Global registry of what each agent can handle."""

    def __init__(self) -> None:
        self._capabilities: dict[str, AgentCapability] = {}

    def register(self, capability: AgentCapability) -> None:
        self._capabilities[capability.agent_id] = capability

    def find(self, task_type: str) -> AgentCapability | None:
        for cap in self._capabilities.values():
            if task_type in cap.task_types:
                return cap
        return None

    def find_all(self, task_type: str) -> list[AgentCapability]:
        return [c for c in self._capabilities.values() if task_type in c.task_types]

    def list_all(self) -> list[AgentCapability]:
        return list(self._capabilities.values())
