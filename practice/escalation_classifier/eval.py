"""Train/test split, train, and report accuracy.

    python practice/escalation_classifier/eval.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from classifier import LogisticClassifier, featurize
from metrics import accuracy

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "tickets.json"


def load_split(seed: int = 7, test_frac: float = 0.25) -> tuple[list[dict], list[dict]]:
    tickets = json.loads(DATA_PATH.read_text())
    rng = random.Random(seed)
    shuffled = tickets[:]
    rng.shuffle(shuffled)
    n_test = int(len(shuffled) * test_frac)
    return shuffled[n_test:], shuffled[:n_test]


def main() -> None:
    train, test = load_split()
    X_train = np.array([featurize(t) for t in train])
    y_train = np.array([1.0 if t["escalated"] else 0.0 for t in train])
    X_test = np.array([featurize(t) for t in test])
    y_test = np.array([1.0 if t["escalated"] else 0.0 for t in test])

    clf = LogisticClassifier(n_features=X_train.shape[1])
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)

    print(f"train size: {len(train)}  test size: {len(test)}")
    print(f"escalation rate (test): {y_test.mean():.2%}")
    print(f"accuracy: {accuracy(y_test, preds):.4f}")


if __name__ == "__main__":
    main()
