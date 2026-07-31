"""Worked reference: extend recall_at_k to separate confident recall from
the abstention rate, rather than silently folding abstentions into either
bucket (an abstention is not the same failure mode as a wrong answer)."""

from __future__ import annotations

from typing import Any


def recall_and_abstention_at_k(
    eval_set: list[dict[str, Any]],
    retriever: Any,
    k: int = 1,
    max_distance: float = 0.40,
) -> dict[str, float]:
    if not eval_set:
        return {"recall_on_confident": 0.0, "abstention_rate": 0.0, "n": 0}

    confident_hits = 0
    confident_total = 0
    abstained = 0

    for item in eval_set:
        matches = retriever.retrieve_with_confidence(item["query"], k=k, max_distance=max_distance)
        if not matches:
            abstained += 1
            continue
        confident_total += 1
        if item["expected_policy_id"] in [pid for pid, _ in matches]:
            confident_hits += 1

    return {
        "recall_on_confident": confident_hits / confident_total if confident_total else 0.0,
        "abstention_rate": abstained / len(eval_set),
        "n": len(eval_set),
    }
