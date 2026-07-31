"""Worked reference solution for the extension task: confidence-threshold
abstention. Not the only valid design — shows one reasonable shape.

Surfaces the embedding distance ChromaDB already computes internally
(discarded by the base retriever.PolicyRetriever.retrieve(), which returns
only policy_ids) and adds a max-distance cutoff: results farther than the
cutoff are treated as "no confident match" instead of a forced top-1 guess.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retriever import PolicyRetriever  # noqa: E402


class PolicyRetrieverWithAbstention(PolicyRetriever):
    def retrieve_with_confidence(
        self, query: str, k: int = 1, max_distance: float = 0.40,
    ) -> list[tuple[str, float]]:
        """Return (policy_id, distance) pairs, filtered to confident matches only.

        max_distance is a cosine-distance cutoff. 0.40 was chosen by actually
        measuring top-1 distances on both eval sets (see NOTES.md): the leaky
        eval set's queries sit unrealistically close to their source policy
        text (mean distance ~0.26, since each query IS a substring of the
        text), while an honest, independently-paraphrased set of the same
        queries sits meaningfully farther (mean ~0.39). At this threshold,
        the leaky set abstains ~20% of the time and the honest set ~45% —
        both have recall_on_confident of 1.0, so the gap isn't about
        accuracy, it's about how confident real customer phrasing actually
        is versus what the leaked eval made it look like.
        """
        n = min(k, len(self._policies))
        results = self._collection.query(query_texts=[query], n_results=n)
        if not results["ids"] or not results["ids"][0]:
            return []
        pairs = list(zip(results["ids"][0], results["distances"][0]))
        return [(pid, dist) for pid, dist in pairs if dist <= max_distance]
