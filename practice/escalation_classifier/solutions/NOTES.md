# Reference notes — Escalation Predictor

All numbers below were measured by actually running this fixture
(`.venv311`, numpy 2.4.6, seed 42 for data generation, seed 7 for the
train/test split) — if you regenerate `tickets.json` or change the
classifier, re-measure before relying on these figures.

## The planted issue: leakage via a post-outcome feature

`assigned_team` is set by the real routing system **after** the escalation
decision has already been made (see `generate_tickets.py`: it's derived
directly from the `escalated` label, with only a 3% mislabel rate). At
prediction time — when this classifier would actually need to run, before a
human or the routing system has looked at the ticket — that field doesn't
exist yet. Training on it is leakage: the model is being handed a
near-perfect encoding of the answer.

This is **not a code bug** in `classifier.py` or `metrics.py` — both are
correct for what they claim to measure. The problem is that one of the input
features was never legitimately available at prediction time.

### The trap: accuracy alone doesn't make it obvious

| | with `assigned_team` (leaky) | without it (fixed) |
|---|---|---|
| accuracy | 0.9818 | 0.9455 |
| escalation precision | 1.0000 | 0.7143 |
| escalation recall | 0.8333 | 0.8333 |

Accuracy drops only slightly (98.2% → 94.6%) — on its own, that could read
as "a small tweak, basically fine." The real tell is **precision**, which
drops sharply (1.00 → 0.71): the leaky feature isn't making the model better
at finding real escalations (recall is identical either way), it's making
it stop making false-positive mistakes it would otherwise make, by handing
it the answer directly. A model that only checks the headline accuracy
number would miss this; checking precision/recall on the minority class
specifically is what surfaces it.

The base rate matters too: escalations are ~11% of the test set, so a
classifier that always predicts "not escalated" would already score ~89%
accuracy. 98.2% sounds good in isolation, but relative to that baseline it's
a smaller jump than it first appears — another reason not to trust a single
aggregate accuracy number on imbalanced data.

## What a strong approach does

- Treats a high accuracy number as worth a second look before assuming the
  classifier is simply good — especially before extending it.
- Checks precision/recall on the minority (escalated) class specifically,
  not just aggregate accuracy, given the ~11% base rate.
- Inspects the feature set and asks, for each feature: "would this actually
  be known at the moment this prediction needs to run?" — `assigned_team`
  fails that test; `category`, `priority`, `customer_tier`, `body_length`
  all pass it.
- Verifies the fix by re-running the numbers with the feature removed,
  rather than reasoning about it in the abstract.

## The extension: confidence-threshold abstention

Reference implementation: `eval_no_leak.py`.

- Removes `assigned_team` from `featurize()` (`include_assigned_team=False`).
- Adds precision/recall on the escalation class, since plain accuracy is a
  weak signal at an ~11% base rate.
- Adds a confidence band (`0.35`–`0.65` predicted probability): tickets
  inside it are routed to a human instead of forcing a binary call.
- Measured result: `abstention_rate = 9.09%`, `recall_on_confident = 0.6667`
  — abstaining on the genuinely ambiguous ~9% of tickets is a real,
  measurable trade-off, not a cosmetic addition. (Note: `recall_on_confident`
  drops below the recall of the un-abstained fixed classifier because
  abstaining removes some of the cases the classifier *was* getting right,
  not just the ones it was getting wrong — worth surfacing as a discussion
  point on where to set the band.)

## Checklist

- [ ] Notices the headline accuracy number is worth a second look
- [ ] Checks precision/recall on the escalation class, not just accuracy
- [ ] Identifies `assigned_team` as unavailable at real prediction time
      (not a code or metric bug)
- [ ] Verifies the fix empirically (re-runs the numbers) rather than by
      assertion
- [ ] Extension: adds precision/recall on the escalation class, adds a
      confidence-band abstention path, and reports its rate/effect
