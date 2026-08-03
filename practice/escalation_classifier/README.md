# Escalation Predictor

A small classifier component. Given a support ticket's intake-time
attributes, it predicts whether the ticket should be routed to escalation
specialists.

## Setup

`numpy` is already a project dependency (see `pyproject.toml`), so no extra
install is needed if you've already run `pip install -e ".[dev]"` for the
main project. No `sklearn` or other ML library is used — the classifier is a
small hand-rolled logistic regression.

```bash
python practice/escalation_classifier/eval.py
```

## What's here

- `tickets.json` — 220 synthetic support tickets (category, priority,
  customer tier, body length, assigned team, and the `escalated` label).
- `classifier.py` — `featurize(ticket)` and `LogisticClassifier`
  (fit/predict, no external ML dependency).
- `metrics.py` — `accuracy(y_true, y_pred)`, the metric already in place.
- `eval.py` — loads the data, splits train/test, trains, and prints
  accuracy.

## Task (45–60 minutes)

1. **Find and fix an existing issue.** Run `eval.py`. Look at the reported
   accuracy. Is it trustworthy? Investigate, and fix whatever you find. The
   classifier code and the metric code are not the only places a problem
   could live.
2. **Extend with a small new capability.** The classifier currently always
   forces a binary escalate/don't-escalate call, even when it isn't
   confident either way. Give it a way to say "route this to a human" for
   the ambiguous cases instead, and update the eval output to reflect it.

Optimise for correctness and clear reasoning about the data and the metric,
not speed.