"""Judge metric -- already in place before the exercise starts."""

from __future__ import annotations

from typing import Any


def judge_pass_rate(eval_set: list[dict[str, Any]], judge: Any) -> float:
    """Fraction of responses the judge rates PASS, based on a single run per example."""
    if not eval_set:
        return 0.0
    passes = 0
    for item in eval_set:
        verdict = judge.judge(item["ticket_body"], item["response"])
        if verdict == "PASS":
            passes += 1
    return passes / len(eval_set)
