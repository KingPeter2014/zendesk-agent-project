"""Layered evaluation metrics matching Braintrust's framework."""

from __future__ import annotations

import time
from typing import Any

from memory.models import EvalMetrics, OutcomeType, Trajectory

# Reference pricing for a comparable hosted 7B-class instruct model. Ollama
# itself runs locally at no per-token cost; these rates stand in for what
# the equivalent hosted inference would cost, so cost tracking is
# meaningful in the dashboard.
INPUT_COST_PER_1K_TOKENS = 0.0001   # $0.10 / 1M input tokens
OUTPUT_COST_PER_1K_TOKENS = 0.0003  # $0.30 / 1M output tokens


def compute_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost for a trajectory's token usage, per the reference pricing above."""
    return (input_tokens / 1000) * INPUT_COST_PER_1K_TOKENS + (output_tokens / 1000) * OUTPUT_COST_PER_1K_TOKENS


def compute_tool_correctness(trajectory: Trajectory, expected_tools: list[str]) -> float:
    """Fraction of expected tool calls that actually appeared in the trajectory."""
    if not expected_tools:
        return 1.0
    actual_tools = [tc.tool_name for step in trajectory.steps for tc in step.tool_calls]
    hits = sum(1 for t in expected_tools if t in actual_tools)
    return hits / len(expected_tools)


def compute_step_efficiency(trajectory: Trajectory, optimal_steps: int) -> float:
    """optimal_steps / actual_steps, capped at 1.0."""
    actual = sum(len(s.tool_calls) for s in trajectory.steps)
    if actual == 0:
        return 1.0 if optimal_steps == 0 else 0.0
    return min(1.0, optimal_steps / actual)


def compute_plan_quality_heuristic(trajectory: Trajectory, objective: str) -> float:
    """
    Heuristic plan quality: awards points for:
    - Having steps
    - No failed tool calls
    - Outcome is resolved or escalated (not failed)
    """
    if not trajectory.steps:
        return 0.0
    score = 0.5  # base for having steps
    errors = sum(1 for s in trajectory.steps for tc in s.tool_calls if tc.error)
    if errors == 0:
        score += 0.3
    if trajectory.outcome in (OutcomeType.RESOLVED, OutcomeType.ESCALATED):
        score += 0.2
    return min(1.0, score)


def compute_safety_score(trajectory: Trajectory, guardrail_triggered: bool) -> float:
    return 0.0 if guardrail_triggered else 1.0


def evaluate_trajectory(
    trajectory: Trajectory,
    scenario_id: str,
    expected_tools: list[str],
    optimal_steps: int,
    objective: str,
    guardrail_triggered: bool = False,
) -> EvalMetrics:
    latency = trajectory.total_latency_ms
    input_tokens = trajectory.input_tokens
    output_tokens = trajectory.output_tokens
    total_tokens = input_tokens + output_tokens

    return EvalMetrics(
        scenario_id=scenario_id,
        ticket_id=trajectory.ticket_id,
        plan_quality=compute_plan_quality_heuristic(trajectory, objective),
        tool_correctness=compute_tool_correctness(trajectory, expected_tools),
        task_completion=trajectory.outcome in (OutcomeType.RESOLVED, OutcomeType.ESCALATED),
        step_efficiency=compute_step_efficiency(trajectory, optimal_steps),
        latency_ms=latency,
        safety_score=compute_safety_score(trajectory, guardrail_triggered),
        outcome=trajectory.outcome,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=compute_cost_usd(input_tokens, output_tokens),
    )
