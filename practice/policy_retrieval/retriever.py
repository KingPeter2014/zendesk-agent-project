"""Policy retriever: semantic search over a small policy corpus (ChromaDB).

Mirrors the shape of memory/vector_memory.py's VectorMemory.retrieve_policy
(same embedding-retrieval approach), kept self-contained here so this
exercise doesn't read or write the app's real data/chroma_db.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings

POLICIES_PATH = Path(__file__).parent / "policies.json"


class PolicyRetriever:
    def __init__(self, policies_path: Path | str = POLICIES_PATH) -> None:
        with open(policies_path) as f:
            self._policies = json.load(f)

        client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
        self._collection = client.get_or_create_collection(
            name="policies", metadata={"hnsw:space": "cosine"},
        )
        self._collection.upsert(
            ids=[p["policy_id"] for p in self._policies],
            documents=[p["text"] for p in self._policies],
            metadatas=[{"category": p["category"]} for p in self._policies],
        )

    def retrieve(self, query: str, k: int = 1) -> list[str]:
        """Return the top-k policy_ids for a query, most relevant first."""
        n = min(k, len(self._policies))
        results = self._collection.query(query_texts=[query], n_results=n)
        if not results["ids"] or not results["ids"][0]:
            return []
        return results["ids"][0]
