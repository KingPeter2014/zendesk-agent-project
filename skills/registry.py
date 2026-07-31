"""Skill registry with metadata, gating, and promotion logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillMetadata:
    name: str
    description: str
    preconditions: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    input_schema: dict[str, str] = field(default_factory=dict)   # param_name -> type hint
    output_schema: dict[str, str] = field(default_factory=dict)
    agent_roles_allowed: list[str] = field(default_factory=list)  # empty = any
    gating_enabled: bool = False        # if True, requires promotion before use
    is_promoted: bool = True            # synthesised skills start False until gated
    invocation_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.invocation_count == 0:
            return 0.0
        return self.success_count / self.invocation_count

    def can_promote(self, min_invocations: int = 10, min_success_rate: float = 0.85) -> bool:
        return (
            self.invocation_count >= min_invocations
            and self.success_rate >= min_success_rate
        )


class SkillRegistry:
    """
    Central registry of callable skills with metadata and gating.
    Skills are stored as (metadata, callable) pairs.
    """

    GATING_MIN_INVOCATIONS = 10
    GATING_MIN_SUCCESS_RATE = 0.85

    def __init__(self) -> None:
        self._skills: dict[str, tuple[SkillMetadata, Callable]] = {}

    def register(self, metadata: SkillMetadata, fn: Callable) -> None:
        self._skills[metadata.name] = (metadata, fn)

    def get(self, name: str) -> tuple[SkillMetadata, Callable] | None:
        return self._skills.get(name)

    def list_available(self, agent_role: str | None = None) -> list[SkillMetadata]:
        result = []
        for meta, _ in self._skills.values():
            if meta.gating_enabled and not meta.is_promoted:
                continue
            if agent_role and meta.agent_roles_allowed and agent_role not in meta.agent_roles_allowed:
                continue
            result.append(meta)
        return result

    def record_invocation(self, name: str, success: bool) -> None:
        if name not in self._skills:
            return
        meta, fn = self._skills[name]
        meta.invocation_count += 1
        if success:
            meta.success_count += 1
        # Auto-promote gated skills that meet the threshold
        if meta.gating_enabled and not meta.is_promoted and meta.can_promote(
            self.GATING_MIN_INVOCATIONS, self.GATING_MIN_SUCCESS_RATE
        ):
            meta.is_promoted = True

    def synthesise_skill(self, metadata: SkillMetadata, fn: Callable) -> None:
        """Add a skill synthesised from traces. Requires gating before use."""
        metadata.gating_enabled = True
        metadata.is_promoted = False
        self.register(metadata, fn)

    def prune_unused(
        self,
        min_invocations: int = 5,
        min_success_rate: float = 0.5,
        protect: list[str] | None = None,
    ) -> list[str]:
        """
        Remove skills that are gated, unused, or consistently failing.
        Built-in skills listed in `protect` are never pruned.
        Returns list of pruned skill names.
        """
        protected = set(protect or [])
        to_prune = []
        for name, (meta, _) in list(self._skills.items()):
            if name in protected:
                continue
            if not meta.gating_enabled:
                continue  # only prune synthesised (gated) skills
            if meta.invocation_count >= min_invocations and meta.success_rate < min_success_rate:
                to_prune.append(name)
            elif meta.invocation_count == 0:
                to_prune.append(name)
        for name in to_prune:
            del self._skills[name]
        return to_prune

    def stats(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "invocations": m.invocation_count,
                "success_rate": round(m.success_rate, 3),
                "promoted": m.is_promoted,
                "gated": m.gating_enabled,
            }
            for m, _ in self._skills.values()
        ]
