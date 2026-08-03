"""Classifier metric — already in place before the exercise starts."""

from __future__ import annotations

import numpy as np


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of predictions that match the true label."""
    return float(np.mean(y_true == y_pred))
