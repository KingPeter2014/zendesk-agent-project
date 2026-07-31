"""Reward functions for offline RL training."""

from __future__ import annotations

from memory.models import OutcomeType, Trajectory


def resolution_success(trajectory: Trajectory) -> float:
    """Binary reward: 1.0 if resolved, 0.5 if escalated, 0.0 if failed/blocked."""
    if trajectory.outcome == OutcomeType.RESOLVED:
        return 1.0
    if trajectory.outcome == OutcomeType.ESCALATED:
        return 0.5
    return 0.0


def efficiency_reward(trajectory: Trajectory, optimal_steps: int = 3) -> float:
    """Reward for resolving in fewer steps than maximum. Capped at 1.0."""
    actual = max(1, sum(len(s.tool_calls) for s in trajectory.steps))
    return min(1.0, optimal_steps / actual)


def escalation_penalty(trajectory: Trajectory) -> float:
    """Small penalty for unnecessary escalations (not for VIP/critical tickets)."""
    if trajectory.outcome == OutcomeType.ESCALATED:
        return -0.3
    return 0.0


def error_penalty(trajectory: Trajectory) -> float:
    """Penalty proportional to the number of tool call errors."""
    errors = sum(1 for s in trajectory.steps for tc in s.tool_calls if tc.error)
    return -0.2 * errors


def latency_reward(trajectory: Trajectory, target_ms: float = 2000.0) -> float:
    """Small bonus for fast resolution; penalty for very slow responses."""
    if trajectory.total_latency_ms <= target_ms:
        return 0.1
    if trajectory.total_latency_ms > target_ms * 5:
        return -0.1
    return 0.0


def composite_reward(
    trajectory: Trajectory,
    optimal_steps: int = 3,
    latency_target_ms: float = 2000.0,
) -> float:
    """
    Composite reward signal combining resolution, efficiency, errors and latency.
    Used as the training reward for offline RL.
    """
    r = (
        resolution_success(trajectory) * 0.5
        + efficiency_reward(trajectory, optimal_steps) * 0.2
        + error_penalty(trajectory) * 0.2
        + latency_reward(trajectory, latency_target_ms) * 0.1
    )
    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, r))


def score_trajectory(trajectory: Trajectory) -> Trajectory:
    """Compute and attach the composite reward to a trajectory in-place."""
    trajectory.reward = composite_reward(trajectory)
    return trajectory
