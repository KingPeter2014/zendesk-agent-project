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
    compute_cost_usd,
    evaluate_trajectory,
    INPUT_COST_PER_1K_TOKENS,
    OUTPUT_COST_PER_1K_TOKENS,
)


def _make_traj(outcome: OutcomeType, tools: list[str], errors: list[bool] | None = None,
                input_tokens: int = 0, output_tokens: int = 0) -> Trajectory:
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
        input_tokens=input_tokens, output_tokens=output_tokens,
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

    def test_token_usage_and_cost_propagated(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order"], input_tokens=120, output_tokens=45)
        metrics = evaluate_trajectory(traj, "sc_tok", ["lookup_order"], 1, "Resolve billing")
        assert metrics.input_tokens == 120
        assert metrics.output_tokens == 45
        assert metrics.total_tokens == 165
        assert metrics.cost_usd == pytest.approx(compute_cost_usd(120, 45))

    def test_zero_tokens_by_default(self):
        traj = _make_traj(OutcomeType.RESOLVED, ["lookup_order"])
        metrics = evaluate_trajectory(traj, "sc_notok", ["lookup_order"], 1, "Resolve billing")
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.cost_usd == 0.0


class TestComputeCostUsd:
    def test_zero_tokens_zero_cost(self):
        assert compute_cost_usd(0, 0) == 0.0

    def test_input_only_cost(self):
        assert compute_cost_usd(1000, 0) == pytest.approx(INPUT_COST_PER_1K_TOKENS)

    def test_output_only_cost(self):
        assert compute_cost_usd(0, 1000) == pytest.approx(OUTPUT_COST_PER_1K_TOKENS)

    def test_combined_cost(self):
        expected = INPUT_COST_PER_1K_TOKENS + OUTPUT_COST_PER_1K_TOKENS
        assert compute_cost_usd(1000, 1000) == pytest.approx(expected)

    def test_output_priced_higher_than_input(self):
        # Guards against an accidental swap of the two rates: hosted-model
        # pricing consistently charges more per output token than input token.
        assert OUTPUT_COST_PER_1K_TOKENS > INPUT_COST_PER_1K_TOKENS

    def test_scales_linearly(self):
        assert compute_cost_usd(2000, 0) == pytest.approx(2 * compute_cost_usd(1000, 0))
