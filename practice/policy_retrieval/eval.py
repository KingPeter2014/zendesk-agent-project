"""Run the eval set through the retriever and report recall@k.

    python practice/policy_retrieval/eval.py
"""

from __future__ import annotations

import json
from pathlib import Path

from metrics import recall_at_k
from retriever import PolicyRetriever

BASE_DIR = Path(__file__).parent
EVAL_SET_PATH = BASE_DIR / "eval_set.json"


def main() -> None:
    with open(EVAL_SET_PATH) as f:
        eval_set = json.load(f)

    retriever = PolicyRetriever()
    score = recall_at_k(eval_set, retriever, k=1)
    print(f"Loaded {len(eval_set)} eval queries.")
    print(f"recall@1 = {score:.1%}")


if __name__ == "__main__":
    main()
