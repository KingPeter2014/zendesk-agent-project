"""Prometheus metrics for all agents, skills, and guardrails."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Agent-level metrics
agent_requests_total = Counter(
    "zendesk_agent_requests_total",
    "Total tickets handled per agent role",
    ["agent_role", "outcome"],
)

agent_latency_seconds = Histogram(
    "zendesk_agent_latency_seconds",
    "End-to-end ticket handling latency",
    ["agent_role"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Skill metrics
skill_invocations_total = Counter(
    "zendesk_skill_invocations_total",
    "Total skill invocations",
    ["skill_name", "success"],
)

# Guardrail metrics
guardrail_blocks_total = Counter(
    "zendesk_guardrail_blocks_total",
    "Requests blocked by guardrails",
    ["guardrail_type", "trigger"],
)

# Memory metrics
memory_version_conflicts_total = Counter(
    "zendesk_memory_version_conflicts_total",
    "Optimistic locking conflicts on shared ticket memory",
)

memory_active_tickets = Gauge(
    "zendesk_memory_active_tickets",
    "Number of tickets currently in shared memory",
)

# A2A delegation metrics
a2a_delegations_total = Counter(
    "zendesk_a2a_delegations_total",
    "Total A2A delegation calls",
    ["task_type", "success"],
)

# RL pipeline
rl_trajectories_total = Counter(
    "zendesk_rl_trajectories_total",
    "Total trajectories logged for RL training",
)


def start_metrics_server(port: int = 8001) -> None:
    start_http_server(port)
    print(f"Prometheus metrics server started on :{port}")
