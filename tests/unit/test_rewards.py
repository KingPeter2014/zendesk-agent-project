"""Unit tests for RL reward functions."""

from __future__ import annotations

import uuid

import pytest

from memory.models import AgentRole, AgentStep, OutcomeType, ToolCall, Trajectory
from rl_pipeline.reward_functions import (
    composite_reward, efficiency_reward, error_penalty, escalation_penalty,
    latency_reward, resolution_success, score_trajectory,
)


def _make_trajectory(outcome: OutcomeType, tool_calls: list[str], errors: list[bool] | None = None) -> Trajectory:
    errors = errors or [False] * len(tool_calls)
    steps = []
    for tc_name, has_error in zip(tool_calls, errors):
        step = AgentStep(
            agent_id="test",
            agent_role=AgentRole.BILLING,
            action=f"execute:{tc_name}",
        )
        step.tool_calls.append(ToolCall(
            tool_name=tc_name,
            inputs={},
            output=None if has_error else {"success": True},
            error="failed" if has_error else None,
            latency_ms=100.0,
        ))
        steps.append(step)
    return Trajectory(
        ticket_id=str(uuid.uuid4()),
        agent_id="test",
        steps=steps,
        outcome=outcome,
        total_latency_ms=len(tool_calls) * 100.0,
    )


class TestRewardFunctions:
    def test_resolved_gets_full_resolution_reward(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order", "process_refund"])
        assert resolution_success(traj) == 1.0

    def test_escalated_gets_partial_reward(self):
        traj = _make_trajectory(OutcomeType.ESCALATED, ["escalate_ticket"])
        assert resolution_success(traj) == 0.5

    def test_failed_gets_zero(self):
        traj = _make_trajectory(OutcomeType.FAILED, [])
        assert resolution_success(traj) == 0.0

    def test_efficient_trajectory(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order", "process_refund", "send_notification"])
        # optimal_steps=3, actual=3 → efficiency=1.0
        assert efficiency_reward(traj, optimal_steps=3) == 1.0

    def test_inefficient_trajectory(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["a", "b", "c", "d", "e", "f"])
        assert efficiency_reward(traj, optimal_steps=2) < 1.0

    def test_error_penalty_applied(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order"], errors=[True])
        assert error_penalty(traj) < 0

    def test_composite_reward_resolved_efficient(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order", "process_refund", "send_notification"])
        r = composite_reward(traj, optimal_steps=3)
        assert r > 0.5

    def test_composite_reward_clamped(self):
        traj = _make_trajectory(OutcomeType.FAILED, ["a"] * 20, errors=[True] * 20)
        r = composite_reward(traj)
        assert -1.0 <= r <= 1.0

    def test_score_trajectory(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["process_refund"])
        scored = score_trajectory(traj)
        assert scored.reward is not None
        assert -1.0 <= scored.reward <= 1.0

    def test_escalation_penalty_when_escalated(self):
        traj = _make_trajectory(OutcomeType.ESCALATED, ["escalate_ticket"])
        assert escalation_penalty(traj) == -0.3

    def test_escalation_penalty_when_resolved(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["process_refund"])
        assert escalation_penalty(traj) == 0.0

    def test_latency_reward_fast(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order"])
        traj.total_latency_ms = 500.0
        assert latency_reward(traj, target_ms=2000.0) == 0.1

    def test_latency_reward_very_slow(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order"])
        traj.total_latency_ms = 15000.0
        assert latency_reward(traj, target_ms=2000.0) == -0.1

    def test_latency_reward_moderate(self):
        traj = _make_trajectory(OutcomeType.RESOLVED, ["lookup_order"])
        traj.total_latency_ms = 5000.0
        assert latency_reward(traj, target_ms=2000.0) == 0.0
