"""ChromaDB-backed long-term vector / episodic memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from memory.models import Trajectory


class VectorMemory:
    """
    Stores episode summaries and retrieves semantically similar past cases.
    Uses ChromaDB in embedded (serverless) mode — no separate process needed.
    """

    def __init__(self, persist_dir: str | Path = "data/chroma_db") -> None:
        persist_dir = Path(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._episodes = self._client.get_or_create_collection(
            name="episodes",
            metadata={"hnsw:space": "cosine"},
        )
        self._policies = self._client.get_or_create_collection(
            name="policies",
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Episodes (resolved tickets)
    # ------------------------------------------------------------------

    def store_episode(
        self,
        trajectory: Trajectory,
        summary: str,
        embedding: list[float] | None = None,
    ) -> None:
        metadata = {
            "ticket_id": trajectory.ticket_id,
            "agent_id": trajectory.agent_id,
            "outcome": trajectory.outcome.value if trajectory.outcome else "unknown",
            "reward": float(trajectory.reward or 0.0),
            "steps": len(trajectory.steps),
        }
        add_kwargs: dict[str, Any] = {
            "ids": [trajectory.trajectory_id],
            "documents": [summary],
            "metadatas": [metadata],
        }
        if embedding is not None:
            add_kwargs["embeddings"] = [embedding]
        self._episodes.upsert(**add_kwargs)

    def retrieve_similar(self, query: str, n: int = 5) -> list[dict[str, Any]]:
        results = self._episodes.query(
            query_texts=[query],
            n_results=min(n, max(1, self._episodes.count())),
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"summary": doc, "metadata": meta, "distance": dist})
        return output

    # ------------------------------------------------------------------
    # Policy facts (company policies for PolicyAgent)
    # ------------------------------------------------------------------

    def store_policy(self, policy_id: str, text: str, category: str) -> None:
        self._policies.upsert(
            ids=[policy_id],
            documents=[text],
            metadatas=[{"category": category}],
        )

    def retrieve_policy(self, query: str, n: int = 3) -> list[str]:
        if self._policies.count() == 0:
            return []
        results = self._policies.query(
            query_texts=[query],
            n_results=min(n, self._policies.count()),
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        return results["documents"][0]

    def seed_policies(self) -> None:
        """Seed a small set of Zendesk demo policies."""
        policies = [
            ("pol_return_30", "Items can be returned within 30 days of delivery for a full refund.", "returns"),
            ("pol_return_electronics", "Electronics have a 14-day return window. Original packaging required.", "returns"),
            ("pol_refund_timeline", "Refunds are processed within 5–7 business days after return is received.", "refunds"),
            ("pol_price_match", "We match competitor prices within 14 days of purchase. Contact support with proof.", "pricing"),
            ("pol_warranty", "All products carry a 12-month manufacturer warranty against defects.", "warranty"),
            ("pol_exchange", "Items can be exchanged for a different colour or size within 30 days.", "exchanges"),
            ("pol_vip_shipping", "VIP members receive free expedited shipping on all orders.", "shipping"),
            ("pol_cancel_order", "Orders can be cancelled before dispatch. Contact support immediately.", "orders"),
        ]
        for pid, text, cat in policies:
            self.store_policy(pid, text, cat)

    def episode_count(self) -> int:
        return self._episodes.count()
