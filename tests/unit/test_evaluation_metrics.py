"""Unit tests for evaluation metrics and harness helpers."""

from __future__ import annotations

import uuid

import pytest

from memory.models import AgentRole, AgentStep, OutcomeType, ToolCall, Trajectory
from evaluation.metrics import (
    compute_plan_quality_heuristic,
    compute_step_efficiency,
    compute_tool_correctness,
    compute_safety_score,
    evaluate_trajectory,
)


def _make_traj(outcome: OutcomeType, tools: list[str], errors: list[bool] | None = None) -> Trajectory:
    errors = errors or [False] * len(tools)
    steps = []
    for name, has_error in zip(tools, errors):
        step = AgentStep(agent_id="a", agent_role=AgentRole.BILLING, action=f"execute:{name}")
        step.tool_calls.append(ToolCall(
            tool_name=name, inputs={},
            error="fail" if has_error else None,
            latency_ms=100.0,
        ))
        steps.append(step)
    traj = Trajectory(
        ticket_id=str(uuid.uuid4()), agent_id="a",
        steps=steps, outcome=outcome, total_latency_ms=len(tools) * 100.0,
    )
    return traj


class TestComputeToolCorrectness:
    def test_perfect(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order", "process_refund"])
        assert compute_tool_correctness(traj, ["lookup_order", "process_refund"]) == 1.0

    def test_partial(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order"])
        assert compute_tool_correctness(traj, ["lookup_order", "process_refund"]) == 0.5

    def test_empty_expected(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order"])
        assert compute_tool_correctness(traj, []) == 1.0

    def test_none_matched(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["send_notification"])
        assert compute_tool_correctness(traj, ["lookup_order", "process_refund"]) == 0.0


class TestComputeStepEfficiency:
    def test_efficient(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["a", "b", "c"])
        assert compute_step_efficiency(traj, optimal_steps=3) == 1.0

    def test_inefficient(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["a", "b", "c", "d", "e"])
        eff = compute_step_efficiency(traj, optimal_steps=2)
        assert eff == pytest.approx(0.4)

    def test_empty_trajectory(self):
        traj = _make_traj(OutcomeType.RESOLVED, [])
        assert compute_step_efficiency(traj, optimal_steps=0) == 1.0

    def test_capped_at_one(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["a"])
        assert compute_step_efficiency(traj, optimal_steps=10) == 1.0


class TestComputePlanQuality:
    def test_resolved_no_errors(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order", "process_refund"])
        score = compute_plan_quality_heuristic(traj, "Resolve billing issue")
        assert score >= 0.9

    def test_failed_with_errors(self):
        traj = _make_traj(OutcomeType.FAILED, ["lookup_order"], errors=[True])
        score = compute_plan_quality_heuristic(traj, "Resolve billing issue")
        assert score < 0.8

    def test_empty_steps(self):
        traj = _make_traj(OutcomeType.FAILED, [])
        assert compute_plan_quality_heuristic(traj, "obj") == 0.0


class TestComputeSafetyScore:
    def test_safe_no_guardrail(self):
        traj = _make_traj(OutcomeType.RESOLVED, [])
        assert compute_safety_score(traj, guardrail_triggered=False) == 1.0

    def test_unsafe_guardrail_fired(self):
        traj = _make_traj(OutcomeType.BLOCKED, [])
        assert compute_safety_score(traj, guardrail_triggered=True) == 0.0


class TestEvaluateTrajectory:
    def test_full_evaluation(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order", "process_refund", "send_notification"])
        metrics = evaluate_trajectory(
            traj, "sc_01",
            expected_tools=["lookup_order", "process_refund", "send_notification"],
            optimal_steps=3,
            objective="Resolve billing",
        )
        assert metrics.scenario_id == "sc_01"
        assert metrics.task_completion is True
        assert metrics.tool_correctness == 1.0
        assert metrics.safety_score == 1.0

    def test_guardrail_triggered_eval(self):
        traj = _make_traj(OutcomeType.BLOCKED, [])
        metrics = evaluate_trajectory(traj, "sc_adv", [], 0, "blocked", guardrail_triggered=True)
        assert metrics.safety_score == 0.0
