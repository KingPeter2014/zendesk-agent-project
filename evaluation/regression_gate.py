"""CI regression gate: fails with exit code 1 if any metric drops >5% vs baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASELINE_PATH = Path("data/baseline_metrics.json")
REGRESSION_THRESHOLD = 0.05  # 5% drop triggers failure

METRICS_TO_CHECK = [
    "avg_plan_quality",
    "avg_tool_correctness",
    "task_completion_rate",
    "avg_safety_score",
]

# Keys that should be saved in the baseline/current report dict
REPORT_KEYS = METRICS_TO_CHECK + ["scenarios_run", "avg_latency_ms"]


def save_baseline(report_dict: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(report_dict, f, indent=2)
    print(f"Baseline saved to {BASELINE_PATH}")


def check_regression(current: dict) -> list[str]:
    if not BASELINE_PATH.exists():
        print("No baseline found. Saving current metrics as baseline.")
        save_baseline(current)
        return []

    with open(BASELINE_PATH) as f:
        baseline = json.load(f)

    failures = []
    for metric in METRICS_TO_CHECK:
        base_val = baseline.get(metric, 0.0)
        curr_val = current.get(metric, 0.0)
        if base_val > 0 and (base_val - curr_val) / base_val > REGRESSION_THRESHOLD:
            failures.append(
                f"REGRESSION: {metric} dropped from {base_val:.3f} to {curr_val:.3f} "
                f"({(base_val - curr_val) / base_val:.1%} > {REGRESSION_THRESHOLD:.0%} threshold)"
            )
    return failures


def main(report_json_path: str | None = None) -> int:
    if report_json_path:
        with open(report_json_path) as f:
            current = json.load(f)
    else:
        # Try reading from stdout-captured file
        print("Usage: python -m evaluation.regression_gate <report.json>")
        return 0

    failures = check_regression(current)
    if failures:
        for f in failures:
            print(f"ERROR: {f}", file=sys.stderr)
        return 1

    print("All metrics within acceptable bounds. No regression detected.")
    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(path))
