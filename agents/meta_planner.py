"""MetaPlannerAgent: hierarchical planner using LangGraph + Ollama."""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict

from langchain_ollama import OllamaLLM
from langgraph.graph import END, START, StateGraph

from a2a.capability_registry import CapabilityRegistry
from a2a.protocol import A2AProtocol
from memory.models import (
    AgentRole, OutcomeType, Plan, PlanStep, Ticket, Trajectory,
)
from memory.working_memory import WorkingMemory
from agents.base_agent import BaseAgent
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


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def _decompose_node(state: PlannerState, llm: OllamaLLM) -> PlannerState:
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

    try:
        response = llm.invoke(prompt)
        # Extract JSON from response (LLMs sometimes wrap in markdown)
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        parsed = json.loads(response[start_idx:end_idx]) if start_idx >= 0 else {}
    except Exception:
        # Fallback: route by category when Ollama is unavailable or returns non-JSON
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
        ollama_model: str = "mistral:7b-instruct",
        ollama_base_url: str = "http://localhost:11434",
        **kwargs: Any,
    ) -> None:
        super().__init__(role=self.ROLE, **kwargs)
        self._capability_registry = capability_registry
        self._protocol = A2AProtocol(capability_registry, self.shared_memory)
        self._llm = OllamaLLM(model=ollama_model, base_url=ollama_base_url, temperature=0.1)
        self._graph = self._build_graph()
        self._execution_engine = ExecutionEngine(self.registry, self.agent_id, self.ROLE)

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

        for note in final_state.get("notes", []):
            self._log_note(ticket.ticket_id, note)

        return trajectory
