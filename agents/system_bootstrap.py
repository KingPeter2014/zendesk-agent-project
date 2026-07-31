"""Wires up the agent system: memory, guardrails, specialist agents, and the meta-planner.

Shared by the FastAPI server, the Streamlit UI, and the demo runner, which each
bootstrap the same core system on top of a differently-obtained `shared_memory`.
"""

from __future__ import annotations

from typing import Any

from a2a.capability_registry import AgentCapability, CapabilityRegistry
from agents.billing_agent import BillingAgent
from agents.escalation_agent import EscalationAgent
from agents.meta_planner import MetaPlannerAgent
from agents.policy_agent import PolicyAgent
from agents.supervisor_agent import SupervisorAgent

BILLING_TASK_TYPES = ["billing", "refund", "charge"]
POLICY_TASK_TYPES = ["policy", "policy_question"]
ESCALATION_TASK_TYPES = ["escalation", "vip_escalation"]


def build_capability_registry(
    billing: BillingAgent, policy: PolicyAgent, escalation: EscalationAgent,
) -> CapabilityRegistry:
    """Register the three specialist agents' delegation handlers."""
    capability_registry = CapabilityRegistry()
    capability_registry.register(AgentCapability(
        agent_id=billing.agent_id, agent_role="billing",
        task_types=BILLING_TASK_TYPES,
        description="Handles billing disputes and refund processing",
        handler=billing.handle_delegation,
    ))
    capability_registry.register(AgentCapability(
        agent_id=policy.agent_id, agent_role="policy",
        task_types=POLICY_TASK_TYPES,
        description="Answers policy and compliance questions",
        handler=policy.handle_delegation,
    ))
    capability_registry.register(AgentCapability(
        agent_id=escalation.agent_id, agent_role="escalation",
        task_types=ESCALATION_TASK_TYPES,
        description="Escalates complex tickets to human specialists",
        handler=escalation.handle_delegation,
    ))
    return capability_registry


def build_agent_graph(
    registry: Any, shared_memory: Any, per_agent_memory: Any, *, with_supervisor: bool = True,
) -> dict[str, Any]:
    """Construct the specialist agents, capability registry, and meta-planner.

    Returns a dict with keys: billing, policy, escalation, supervisor (None if
    `with_supervisor` is False), capability_registry, meta_planner.
    """
    agent_kwargs = dict(registry=registry, shared_memory=shared_memory, per_agent_memory=per_agent_memory)
    billing = BillingAgent(**agent_kwargs)
    policy = PolicyAgent(**agent_kwargs)
    escalation = EscalationAgent(**agent_kwargs)
    supervisor = SupervisorAgent(**agent_kwargs) if with_supervisor else None

    capability_registry = build_capability_registry(billing, policy, escalation)
    meta_planner = MetaPlannerAgent(capability_registry=capability_registry, **agent_kwargs)

    return {
        "billing": billing,
        "policy": policy,
        "escalation": escalation,
        "supervisor": supervisor,
        "capability_registry": capability_registry,
        "meta_planner": meta_planner,
    }


def build_full_system(shared_memory: Any) -> dict[str, Any]:
    """Build the full runtime bundle on top of an already-constructed `shared_memory`.

    Used by both the Streamlit UI (which pre-builds `shared_memory` to probe Redis
    connectivity) and the demo runner. `shared_memory` may be None if the caller
    couldn't connect — agents and the harness tolerate that the same way as before.
    """
    from memory.per_agent_memory import PerAgentMemory
    from memory.vector_memory import VectorMemory
    from skills.builtin.register import build_default_registry
    from guardrails.input_guardrails import InputGuardrails
    from guardrails.output_guardrails import OutputGuardrails
    from guardrails.governance import GovernanceGuardrails
    from rl_pipeline.trajectory_logger import TrajectoryLogger
    from rl_pipeline.reward_functions import score_trajectory
    from evaluation.harness import EvaluationHarness

    per_agent_memory = PerAgentMemory()
    vector_memory = VectorMemory()
    vector_memory.seed_policies()
    registry = build_default_registry()
    trajectory_logger = TrajectoryLogger()
    input_guardrails = InputGuardrails()
    output_guardrails = OutputGuardrails()
    governance = GovernanceGuardrails()

    graph = build_agent_graph(registry, shared_memory, per_agent_memory)

    return {
        "shared_memory": shared_memory,
        "per_agent_memory": per_agent_memory,
        "vector_memory": vector_memory,
        "registry": registry,
        "trajectory_logger": trajectory_logger,
        "input_guardrails": input_guardrails,
        "output_guardrails": output_guardrails,
        "governance": governance,
        "billing": graph["billing"],
        "policy": graph["policy"],
        "escalation": graph["escalation"],
        "supervisor": graph["supervisor"],
        "meta_planner": graph["meta_planner"],
        "capability_registry": graph["capability_registry"],
        "harness": EvaluationHarness(shared_memory, input_guardrails),
        "score_trajectory": score_trajectory,
    }
