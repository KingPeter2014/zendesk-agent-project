"""Reference solution: remove the leaky feature, add class-aware metrics and
confidence-threshold abstention (the extension).

    python practice/escalation_classifier/solutions/eval_no_leak.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier import LogisticClassifier, featurize  # noqa: E402
from metrics import accuracy  # noqa: E402

DATA_PATH = Path(__file__).parent.parent / "tickets.json"


def load_split(seed: int = 7, test_frac: float = 0.25) -> tuple[list[dict], list[dict]]:
    tickets = json.loads(DATA_PATH.read_text())
    rng = random.Random(seed)
    shuffled = tickets[:]
    rng.shuffle(shuffled)
    n_test = int(len(shuffled) * test_frac)
    return shuffled[n_test:], shuffled[:n_test]


def precision_recall(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    tp = float(np.sum((y_pred == 1) & (y_true == 1)))
    fp = float(np.sum((y_pred == 1) & (y_true == 0)))
    fn = float(np.sum((y_pred == 0) & (y_true == 1)))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def run(include_assigned_team: bool, label: str) -> np.ndarray:
    train, test = load_split()
    X_train = np.array([featurize(t, include_assigned_team) for t in train])
    y_train = np.array([1.0 if t["escalated"] else 0.0 for t in train])
    X_test = np.array([featurize(t, include_assigned_team) for t in test])
    y_test = np.array([1.0 if t["escalated"] else 0.0 for t in test])

    clf = LogisticClassifier(n_features=X_train.shape[1])
    clf.fit(X_train, y_train)
    proba = clf.predict_proba(X_test)
    preds = (proba >= 0.5).astype(int)

    precision, recall = precision_recall(y_test, preds)
    print(f"--- {label} ---")
    print(f"accuracy:              {accuracy(y_test, preds):.4f}")
    print(f"escalation precision:  {precision:.4f}")
    print(f"escalation recall:     {recall:.4f}")
    print(f"escalation rate (test): {y_test.mean():.2%}")
    return proba, y_test


def abstention_report(proba: np.ndarray, y_test: np.ndarray, low: float, high: float) -> None:
    """Abstain (route to human triage) when the model isn't confident either way."""
    confident = (proba <= low) | (proba >= high)
    preds = (proba >= 0.5).astype(int)

    abstention_rate = 1.0 - confident.mean()
    if confident.sum() > 0:
        recall_on_confident_denom = float(np.sum((y_test == 1) & confident))
        recall_on_confident = (
            float(np.sum((preds == 1) & (y_test == 1) & confident)) / recall_on_confident_denom
            if recall_on_confident_denom
            else float("nan")
        )
    else:
        recall_on_confident = float("nan")

    print(f"\n--- abstention (confidence band {low:.2f}-{high:.2f}) ---")
    print(f"abstention_rate:       {abstention_rate:.2%}")
    print(f"recall_on_confident:   {recall_on_confident:.4f}")


def main() -> None:
    run(include_assigned_team=True, label="WITH leaky assigned_team feature")
    print()
    proba, y_test = run(include_assigned_team=False, label="WITHOUT leaky feature (fixed)")
    abstention_report(proba, y_test, low=0.35, high=0.65)


if __name__ == "__main__":
    main()
