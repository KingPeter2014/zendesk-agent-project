"""Unit tests for TrajectoryLogger."""

from __future__ import annotations

import uuid

import pytest

from memory.models import AgentRole, AgentStep, OutcomeType, ToolCall, Trajectory
from rl_pipeline.trajectory_logger import TrajectoryLogger


def _make_trajectory(outcome: OutcomeType = OutcomeType.RESOLVED) -> Trajectory:
    step = AgentStep(agent_id="a", agent_role=AgentRole.BILLING, action="execute:process_refund")
    step.tool_calls.append(ToolCall(tool_name="process_refund", inputs={"order_id": "x"}, latency_ms=50.0))
    return Trajectory(
        ticket_id=str(uuid.uuid4()),
        agent_id="test-agent",
        steps=[step],
        outcome=outcome,
        reward=0.8,
        total_latency_ms=50.0,
    )


@pytest.fixture
def logger(tmp_path):
    return TrajectoryLogger(db_path=tmp_path / "test_trajectories.db")


class TestTrajectoryLogger:
    def test_log_and_count(self, logger):
        traj = _make_trajectory()
        logger.log(traj)
        assert logger.count() == 1

    def test_log_multiple(self, logger):
        for _ in range(5):
            logger.log(_make_trajectory())
        assert logger.count() == 5

    def test_fetch_all_returns_records(self, logger):
        traj = _make_trajectory(OutcomeType.ESCALATED)
        logger.log(traj)
        records = logger.fetch_all()
        assert len(records) == 1
        assert records[0]["outcome"] == "escalated"
        assert records[0]["reward"] == 0.8
        assert records[0]["trajectory_id"] == traj.trajectory_id

    def test_fetch_all_empty(self, logger):
        assert logger.fetch_all() == []

    def test_upsert_same_id(self, logger):
        traj = _make_trajectory()
        logger.log(traj)
        traj.reward = 0.99
        logger.log(traj)  # should upsert, not duplicate
        assert logger.count() == 1
        records = logger.fetch_all()
        assert records[0]["reward"] == 0.99

    def test_failed_trajectory_logged(self, logger):
        traj = _make_trajectory(OutcomeType.FAILED)
        traj.reward = -0.3
        logger.log(traj)
        records = logger.fetch_all()
        assert records[0]["outcome"] == "failed"

    def test_steps_preserved_as_json(self, logger):
        traj = _make_trajectory()
        logger.log(traj)
        records = logger.fetch_all()
        steps = records[0]["steps"]
        assert isinstance(steps, list)
        assert len(steps) == 1
        assert steps[0]["tool_calls"][0]["tool_name"] == "process_refund"
