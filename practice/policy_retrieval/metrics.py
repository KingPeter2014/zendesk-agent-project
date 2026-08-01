"""Retrieval metric — already in place before the exercise starts."""

from __future__ import annotations

from typing import Any


def recall_at_k(eval_set: list[dict[str, Any]], retriever: Any, k: int = 1) -> float:
    """Fraction of eval queries whose expected policy_id appears in the top-k results."""
    if not eval_set:
        return 0.0
    hits = 0
    for item in eval_set:
        top_k = retriever.retrieve(item["query"], k=k)
        if item["expected_policy_id"] in top_k:
            hits += 1
    return hits / len(eval_set)
