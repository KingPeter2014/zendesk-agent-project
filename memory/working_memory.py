"""In-process working memory for a single agent turn."""

from __future__ import annotations

from typing import Any

from memory.models import Plan, ToolCall


class WorkingMemory:
    """Holds the active plan, intermediate tool results, and reasoning for one agent session."""

    def __init__(self, ticket_id: str, agent_id: str) -> None:
        self.ticket_id = ticket_id
        self.agent_id = agent_id
        self.plan: Plan | None = None
        self.tool_results: dict[str, Any] = {}
        self.tool_call_log: list[ToolCall] = []
        self.reasoning_trace: list[str] = []
        self.clarification_needed: bool = False
        self.clarification_question: str | None = None

    def set_plan(self, plan: Plan) -> None:
        self.plan = plan

    def record_tool_call(self, tool_call: ToolCall, result_key: str | None = None) -> None:
        self.tool_call_log.append(tool_call)
        if result_key and tool_call.output is not None:
            self.tool_results[result_key] = tool_call.output

    def add_reasoning(self, thought: str) -> None:
        self.reasoning_trace.append(thought)

    def request_clarification(self, question: str) -> None:
        self.clarification_needed = True
        self.clarification_question = question

    def summarise_context(self, max_chars: int = 500) -> str:
        """
        Produce a compact summary of the working context for context-window management.
        Used when passing context to sub-agents to avoid token bloat.
        """
        parts = [f"ticket={self.ticket_id[:8]}"]
        if self.plan:
            parts.append(f"plan={self.plan.plan_id[:8]} steps={len(self.plan.steps)}")
        if self.tool_results:
            keys = list(self.tool_results.keys())
            parts.append(f"results=[{', '.join(keys[:5])}]")
        if self.reasoning_trace:
            last = self.reasoning_trace[-1][:80]
            parts.append(f"last_thought={last!r}")
        summary = " | ".join(parts)
        return summary[:max_chars]

    def snapshot(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "agent_id": self.agent_id,
            "plan_id": self.plan.plan_id if self.plan else None,
            "tool_results": self.tool_results,
            "reasoning_steps": len(self.reasoning_trace),
            "tool_calls": len(self.tool_call_log),
            "clarification_needed": self.clarification_needed,
        }
