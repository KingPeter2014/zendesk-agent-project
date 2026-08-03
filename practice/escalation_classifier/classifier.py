"""Small logistic-regression classifier for the escalation-prediction task."""

from __future__ import annotations

import numpy as np

CATEGORIES = ["billing_dispute", "order_issue", "policy_question", "vip_escalation", "off_topic"]
PRIORITIES = ["low", "medium", "high", "critical"]
TIERS = ["standard", "premium", "vip"]
TEAMS = ["general_support", "escalation_specialists"]


def featurize(ticket: dict, include_assigned_team: bool = True) -> np.ndarray:
    """Turn a ticket dict into a numeric feature vector."""
    category = [1.0 if ticket["category"] == c else 0.0 for c in CATEGORIES]
    priority = [float(PRIORITIES.index(ticket["priority"]))]
    tier = [float(TIERS.index(ticket["customer_tier"]))]
    body_length = [ticket["body_length"] / 100.0]
    features = category + priority + tier + body_length
    if include_assigned_team:
        features += [1.0 if ticket["assigned_team"] == t else 0.0 for t in TEAMS]
    return np.array(features, dtype=float)


class LogisticClassifier:
    """Plain logistic regression, trained by gradient descent. No external ML deps."""

    def __init__(self, n_features: int, lr: float = 0.1, epochs: int = 500) -> None:
        self.weights = np.zeros(n_features)
        self.bias = 0.0
        self.lr = lr
        self.epochs = epochs

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        n = X.shape[0]
        for _ in range(self.epochs):
            z = X @ self.weights + self.bias
            preds = 1.0 / (1.0 + np.exp(-z))
            grad_w = X.T @ (preds - y) / n
            grad_b = float(np.mean(preds - y))
            self.weights -= self.lr * grad_w
            self.bias -= self.lr * grad_b

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        z = X @ self.weights + self.bias
        return 1.0 / (1.0 + np.exp(-z))

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)
