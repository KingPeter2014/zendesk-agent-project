"""MetaPlannerAgent: hierarchical planner using LangGraph + a switchable LLM provider."""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

import config
from a2a.capability_registry import CapabilityRegistry
from a2a.protocol import A2AProtocol
from memory.models import (
    AgentRole, OutcomeType, Plan, PlanStep, Ticket, Trajectory,
)
from memory.working_memory import WorkingMemory
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient, create_llm_client
from observability.tracing import traced
from skills.execution_engine import ExecutionEngine
from skills.registry import SkillRegistry


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class PlannerState(TypedDict):
    ticket: dict
    objective: str
    clarification_needed: bool
    clarification_question: str
    plan_steps: list[dict]
    delegate_task: str | None
    delegate_inputs: dict
    outcome: str | None
    notes: list[str]
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def _decompose_node(state: PlannerState, llm: LLMClient) -> PlannerState:
    ticket = state["ticket"]
    body = ticket.get("body", "")
    category = ticket.get("category", "")

    prompt = f"""You are a customer service agent planner.
Ticket category: {category}
Ticket body: {body}

Decide:
1. Is clarification needed? (yes/no)
2. If no clarification needed, what is the main objective?
3. Which specialist should handle this? Options: billing, policy, escalation, self
4. What is the single most important action?

Reply in JSON only:
{{"clarification_needed": false, "objective": "...", "delegate_to": "billing|policy|escalation|self", "action_reason": "..."}}"""

    input_tokens = 0
    output_tokens = 0
    try:
        result = llm.complete(prompt)
        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
        # Extract JSON from response (LLMs sometimes wrap in markdown)
        start_idx = result.text.find("{")
        end_idx = result.text.rfind("}") + 1
        parsed = json.loads(result.text[start_idx:end_idx]) if start_idx >= 0 else {}
    except Exception:
        # Fallback: route by category when the LLM provider is unavailable or returns non-JSON
        parsed = {}

    clarification_needed = bool(parsed.get("clarification_needed", False))
    objective = str(parsed.get("objective", f"Resolve {category} ticket"))
    delegate_to = str(parsed.get("delegate_to", "self"))

    # Map vip_escalation category to escalation agent
    if category == "vip_escalation" or ticket.get("priority") in ("high", "critical"):
        delegate_to = "escalation"
    elif category == "billing_dispute":
        delegate_to = "billing"
    elif category == "policy_question":
        delegate_to = "policy"
    elif category == "off_topic":
        clarification_needed = True

    return {
        **state,
        "objective": objective,
        "clarification_needed": clarification_needed,
        "delegate_task": None if delegate_to == "self" else delegate_to,
        "notes": state["notes"] + [f"Decomposed: delegate_to={delegate_to}"],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _clarify_node(state: PlannerState) -> PlannerState:
    ticket_body = state["ticket"].get("body", "")
    question = "Could you please clarify what specific assistance you need regarding your request?"
    return {
        **state,
        "clarification_question": question,
        "outcome": OutcomeType.CLARIFICATION_NEEDED.value,
        "notes": state["notes"] + [f"Clarification requested: {question}"],
    }


def _self_handle_node(state: PlannerState) -> PlannerState:
    # Meta-planner handles simple / off-topic tickets directly
    category = state["ticket"].get("category", "")
    if category == "off_topic":
        return {
            **state,
            "plan_steps": [
                {"skill_name": "send_notification", "inputs": {
                    "customer_id": state["ticket"].get("customer_id", ""),
                    "message": "Thank you for reaching out. This appears to be outside our support scope. "
                               "Please visit our help centre for further assistance.",
                    "channel": "email",
                }}
            ],
            "outcome": OutcomeType.RESOLVED.value,
            "notes": state["notes"] + ["Off-topic handled with polite redirect"],
        }
    return {
        **state,
        "plan_steps": [],
        "outcome": OutcomeType.RESOLVED.value,
    }


def _delegate_node(state: PlannerState, protocol: A2AProtocol, ticket_id: str) -> PlannerState:
    task_type = state["delegate_task"]
    result = protocol.delegate(
        task_type=task_type,
        delegating_agent="meta_planner",
        ticket_id=ticket_id,
        inputs=state.get("delegate_inputs", {}),
    )
    outcome = OutcomeType.RESOLVED.value if result.success else OutcomeType.FAILED.value
    notes = state["notes"] + [
        f"Delegated {task_type}: success={result.success}"
        + (f", error={result.error}" if result.error else "")
    ]
    return {**state, "outcome": outcome, "notes": notes}


def _route_after_decompose(state: PlannerState) -> Literal["clarify", "delegate", "self_handle"]:
    if state["clarification_needed"]:
        return "clarify"
    if state["delegate_task"]:
        return "delegate"
    return "self_handle"


# ---------------------------------------------------------------------------
# MetaPlannerAgent
# ---------------------------------------------------------------------------

class MetaPlannerAgent(BaseAgent):

    ROLE = AgentRole.META_PLANNER

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        llm_provider: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(role=self.ROLE, **kwargs)
        self._capability_registry = capability_registry
        self._protocol = A2AProtocol(capability_registry, self.shared_memory)
        self._llm: LLMClient = create_llm_client(llm_provider or config.LLM_PROVIDER)
        self._graph = self._build_graph()
        self._execution_engine = ExecutionEngine(self.registry, self.agent_id, self.ROLE)

    @property
    def llm_provider(self) -> str:
        return self._llm.provider_name

    def switch_provider(self, provider: str, **overrides: str) -> None:
        """Swap the active LLM client at runtime.

        The `decompose` graph node closes over `self` (not a snapshot of
        `self._llm`), so reassigning `self._llm` here takes effect on the very
        next `.handle()` call — no graph rebuild needed.
        """
        self._llm = create_llm_client(provider, **overrides)

    def _build_graph(self) -> Any:
        builder: StateGraph = StateGraph(PlannerState)

        builder.add_node("decompose", lambda s: _decompose_node(s, self._llm))
        builder.add_node("clarify", _clarify_node)
        builder.add_node("delegate", lambda s: _delegate_node(s, self._protocol, s["ticket"]["ticket_id"]))
        builder.add_node("self_handle", _self_handle_node)

        builder.add_edge(START, "decompose")
        builder.add_conditional_edges("decompose", _route_after_decompose)
        builder.add_edge("clarify", END)
        builder.add_edge("delegate", END)
        builder.add_edge("self_handle", END)

        return builder.compile()

    @traced("meta_planner.handle")
    def handle(self, ticket: Ticket, context: dict[str, Any] | None = None) -> Trajectory:
        ctx = context or {}
        wm = WorkingMemory(ticket_id=ticket.ticket_id, agent_id=self.agent_id)

        initial_state: PlannerState = {
            "ticket": ticket.model_dump(mode="json"),
            "objective": "",
            "clarification_needed": False,
            "clarification_question": "",
            "plan_steps": [],
            "delegate_task": None,
            "delegate_inputs": ctx,
            "outcome": None,
            "notes": [],
            "input_tokens": 0,
            "output_tokens": 0,
        }

        final_state = self._graph.invoke(initial_state)

        # Build a trajectory from graph execution
        trajectory = Trajectory(
            ticket_id=ticket.ticket_id,
            agent_id=self.agent_id,
        )

        # If self-handled steps exist, execute them
        if final_state.get("plan_steps"):
            plan = Plan(
                ticket_id=ticket.ticket_id,
                objective=final_state["objective"],
                steps=[
                    PlanStep(
                        skill_name=s["skill_name"],
                        inputs=s.get("inputs", {}),
                    )
                    for s in final_state["plan_steps"]
                ],
            )
            trajectory = self._execution_engine.execute(plan, wm, ctx)

        raw_outcome = final_state.get("outcome")
        if raw_outcome:
            trajectory.outcome = OutcomeType(raw_outcome)

        trajectory.input_tokens = final_state.get("input_tokens", 0)
        trajectory.output_tokens = final_state.get("output_tokens", 0)

        for note in final_state.get("notes", []):
            self._log_note(ticket.ticket_id, note)

        return trajectory
