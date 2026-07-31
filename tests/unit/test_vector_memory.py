"""Unit tests for VectorMemory (ChromaDB embedded)."""

from __future__ import annotations

import pytest

from memory.models import AgentRole, AgentStep, OutcomeType, ToolCall, Trajectory
from memory.vector_memory import VectorMemory


@pytest.fixture
def vector_memory(tmp_path):
    return VectorMemory(persist_dir=tmp_path / "chroma")


def _make_trajectory(outcome: OutcomeType = OutcomeType.RESOLVED) -> Trajectory:
    return Trajectory(ticket_id="ticket-001", agent_id="agent-001", outcome=outcome)


class TestVectorMemory:
    def test_episode_count_starts_at_zero(self, vector_memory):
        assert vector_memory.episode_count() == 0

    def test_store_episode_increments_count(self, vector_memory):
        traj = _make_trajectory()
        vector_memory.store_episode(traj, summary="Customer refund resolved")
        assert vector_memory.episode_count() == 1

    def test_store_multiple_episodes(self, vector_memory):
        for i in range(3):
            traj = Trajectory(ticket_id=f"t{i}", agent_id="a", outcome=OutcomeType.RESOLVED)
            vector_memory.store_episode(traj, summary=f"Episode {i} summary")
        assert vector_memory.episode_count() == 3

    def test_retrieve_similar_empty_store(self, vector_memory):
        result = vector_memory.retrieve_similar("refund question")
        assert result == []

    def test_retrieve_similar_after_store(self, vector_memory):
        traj = _make_trajectory()
        vector_memory.store_episode(traj, summary="Billing dispute resolved with full refund")
        results = vector_memory.retrieve_similar("billing refund", n=1)
        assert len(results) == 1
        assert "summary" in results[0]
        assert "metadata" in results[0]
        assert "distance" in results[0]

    def test_retrieve_similar_metadata_fields(self, vector_memory):
        traj = _make_trajectory(OutcomeType.ESCALATED)
        traj.reward = 0.5
        vector_memory.store_episode(traj, summary="VIP customer escalation")
        results = vector_memory.retrieve_similar("vip escalation", n=1)
        assert results[0]["metadata"]["outcome"] == "escalated"
        assert results[0]["metadata"]["ticket_id"] == "ticket-001"

    def test_upsert_overwrites_existing(self, vector_memory):
        traj = _make_trajectory()
        vector_memory.store_episode(traj, summary="First summary")
        vector_memory.store_episode(traj, summary="Updated summary")
        assert vector_memory.episode_count() == 1

    def test_store_episode_with_custom_embedding(self, vector_memory):
        traj = _make_trajectory()
        embedding = [0.0] * 384
        vector_memory.store_episode(traj, summary="Embedded episode", embedding=embedding)
        assert vector_memory.episode_count() == 1

    def test_store_policy_and_retrieve(self, vector_memory):
        vector_memory.store_policy("pol_1", "Return within 30 days for a full refund", "returns")
        results = vector_memory.retrieve_policy("return policy")
        assert len(results) >= 1
        assert any("Return" in r or "return" in r for r in results)

    def test_retrieve_policy_empty_store(self, vector_memory):
        results = vector_memory.retrieve_policy("anything")
        assert results == []

    def test_seed_policies_populates_store(self, vector_memory):
        vector_memory.seed_policies()
        results = vector_memory.retrieve_policy("return policy")
        assert len(results) > 0

    def test_seed_policies_idempotent(self, vector_memory):
        vector_memory.seed_policies()
        vector_memory.seed_policies()
        results = vector_memory.retrieve_policy("warranty")
        assert len(results) > 0

    def test_retrieve_policy_respects_n_limit(self, vector_memory):
        vector_memory.seed_policies()
        results = vector_memory.retrieve_policy("return refund policy", n=2)
        assert len(results) <= 2
