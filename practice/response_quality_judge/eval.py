"""Run the eval set through the judge and report the pass rate.

    python practice/response_quality_judge/eval.py

Requires Ollama running locally with mistral:7b-instruct pulled
(`docker-compose up -d` from the project root; see the main README).
"""

from __future__ import annotations

import json
from pathlib import Path

from judge import LLMJudge
from metrics import judge_pass_rate

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "tickets.json"


def main() -> None:
    with open(DATA_PATH) as f:
        eval_set = json.load(f)

    judge = LLMJudge()
    score = judge_pass_rate(eval_set, judge)
    print(f"Loaded {len(eval_set)} ticket/response pairs.")
    print(f"judge_pass_rate = {score:.1%}")


if __name__ == "__main__":
    main()
