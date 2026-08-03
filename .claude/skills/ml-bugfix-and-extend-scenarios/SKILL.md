---
name: ml-bugfix-and-extend-scenarios
description: "Use for live-coding, repo-walkthrough, or pairing-style practice exercises centred on a model-driven component (retrieval/RAG, classifier, ranker, prompt-based system, data pipeline step, or agent tool-calling component) with a small dataset and a metric already in place: find and fix a planted issue, then extend with a small new capability. Also use to design, build, or review such practice scenarios against this repo as a stand-in codebase. Pairs with repo-bugfix-and-extend for the general method. Triggers: live coding exercise, repo walkthrough exercise, pairing exercise, model component exercise, planted bug, find the bug in this component, data leakage, train/test contamination, LLM-as-judge, metric looks wrong but isn't, build a practice scenario, design a practice exercise."
---

# Model-Driven Component: Find, Fix & Extend

A framework for practicing (or building practice material for) exercises
centred on a model-driven component: a partially built repo, a small
dataset, a metric already in place, a planted issue to find and fix, and a
small new capability to add. This format shows up in pairing sessions,
workshops, take-home exercises, and self-directed practice — it isn't tied
to one specific program.

**Before using this skill, check for:** any specific brief or rubric already
provided (component type, time budget, what's being evaluated, whether
AI-assisted tools are expected). Use those specifics wherever available —
the defaults below are reasonable fallbacks, not a claim about any one
program's actual format.

## Format (typically 45–60 min)

Live pairing or solo work in a partially built repo, usually provided
shortly before to clone and confirm it runs. Not a puzzle/algorithm test —
it simulates real day-to-day work on a model-driven component.

- Centres on a model-driven component (see the scenario catalog below for
  the range of shapes) with a small dataset and a metric already in place.
- Two parts: **(a)** find and fix an existing planted issue, **(b)** extend
  with a small new capability.
- What matters: correctness, reasoning about the data/metric, and how the
  fix is verified — not speed.
- AI-assisted tools are often expected in this format — the value is in the
  real workflow: how you prompt, how you verify the output, and when you
  choose to hand-write instead. Confirm whether tool use is expected before
  assuming it.
- What this format tends to surface: statistical/evaluation fundamentals
  (leakage, metric choice, overfitting, sampling), clean/defensive coding,
  structured debugging, clear communication.
- If an LLM-as-judge is involved anywhere: be ready to justify why the judge
  is trustworthy — validate against human labels, check inter-rater
  agreement, and explain why one run / one score is not enough for a
  probabilistic system.

**Working method** — pairs with `repo-bugfix-and-extend`'s general
orient/reproduce/hypothesize/isolate/extend/verify method; this is the
ML-specific emphasis within it:
1. Read the metric/eval code *before* touching the model/retrieval code —
   the bug is as likely to be in the metric as in the pipeline.
2. State a hypothesis out loud before changing anything ("this metric looks
   like it's rewarding X regardless of Y — let me check").
3. Write or run a test that isolates the bug before fixing it (red), then
   confirm the fix (green) — don't just eyeball it.
4. For the extension: keep it small and validate it against the *same*
   metric/eval path used for the fix, not a new ad hoc check.

## Scenario catalog

Recognize these shapes rather than expecting only one. `repo-bugfix-and-extend`
Step 3 already prioritizes the base bug categories (data leakage,
train/test contamination, a metric quietly measuring the wrong thing) — the
lists below are the ML-flavored specialization of those, broadened across
component shapes.

### By component shape

- **Retrieval / RAG component** — semantic search over a corpus. Classic
  leakage via near-duplicate or substring eval queries; classic bad-metric
  via checking substring containment instead of true relevance.
- **Classifier** — leakage via a feature derived from the label itself or
  from post-outcome data; contamination via near-duplicate rows crossing
  train/test (templated data generation is a common cause); a bad metric
  via plain accuracy on an imbalanced set masking a majority-class
  classifier.
- **Ranking / scoring function** — bad-metric via optimizing a proxy that
  doesn't track the real objective (e.g. a ranking metric computed over the
  wrong relevance labels); leakage via features that encode
  future/ground-truth information not available at inference time.
- **Prompt-based / LLM-call component** — LLM-as-judge trustworthiness gaps
  (a single run treated as ground truth); non-determinism/flakiness masking
  a real regression; a silent fallback (catching an exception and returning
  a default) that looks like success in aggregate metrics.
- **Data pipeline / ETL step** — a train/test split applied on the wrong
  unit of independence (e.g. splitting rows instead of splitting entities,
  letting the same entity appear on both sides); deduplication skipped
  before the split.
- **Agent / tool-calling component** — a tool-correctness metric that
  credits a call as "correct" because it ran without error, not because it
  returned the right result.

### By bug category

- **Data leakage** — an eval example derived from the same source as what
  it's testing (a substring, a near-duplicate, or a transformation of the
  label itself).
- **Train/test contamination** — near-duplicate or templated rows crossing
  a split; a split applied on the wrong unit of independence.
- **A metric quietly measuring the wrong thing** — checks a proxy
  (containment, non-empty response, absence of an exception) instead of the
  real target; an LLM-as-judge whose reliability was never checked; an
  aggregate metric that hides a systematic subgroup failure.
- **Miscalibration** — a threshold/cutoff tuned against a leaky or
  non-representative set, producing a cutoff that looks right on paper but
  is wrong once deployed.

## Worked example: Policy Answer Retrieval (RAG-shaped, data leakage)

A fully built practice ground matching the retrieval-component shape above.

**Framing:** "Small policy-answering component. It retrieves the most
relevant company policy for a customer query via semantic search over a
policy corpus (reuses this repo's real
[memory/vector_memory.py](memory/vector_memory.py)
`VectorMemory.retrieve_policy`, backed by ChromaDB — genuine embedding
retrieval, not the trivial keyword map in
[skills/builtin/check_policy.py](skills/builtin/check_policy.py)). An eval
script with a `recall_at_k` metric is already wired up and reports 100%
recall@1. Investigate, then add [extension]."

**The dataset:**
- `policies.json` — ~10 short policy docs (reuse the 8 already seeded by
  `VectorMemory.seed_policies()` plus 2 more).
- `eval_set.json` — ~20 labelled `(query, expected_policy_id)` pairs.

**The metric already in place:** `recall_at_k(eval_set, retriever, k=1)` —
fraction of queries where the expected policy_id is in the top-k retrieved
results. Reports 100%.

**The planted issue (leakage, lives in the data, not the code):**
`eval_set.json` was generated by taking verbatim substrings of the policy
text itself as the "query" (e.g. policy *"Items can be returned within 30
days of delivery for a full refund."* → eval query *"returned within 30 days
of delivery"*). Since the same embedding model embeds both documents and
queries, and the query is literally a substring of the indexed document,
cosine similarity is near-1.0 — recall@1 = 100% regardless of whether the
retriever generalizes to real, paraphrased language at all. The eval set is
not independent of the index it's scored against — classic data leakage,
and it looks completely healthy until inspected.

**Important — verified empirically, don't assume:** an honestly paraphrased,
independent eval set of the same 20 queries *also* scores `recall@1 = 100%`
on this fixture (the 10-policy corpus is small and topically well-separated,
so top-1 label accuracy is easy either way). The leak does **not** reveal
itself as a recall drop. The real, measured tell is retrieval *confidence*:
leaked queries sit unrealistically close to their source documents (mean
top-1 distance 0.256) versus honest paraphrases (mean 0.394) — a real,
~54%-higher gap — but that distance is never surfaced by the retriever as
given. This is a better exercise than a simple recall-drop would have been:
it punishes stopping at "recall didn't change, so it's fine" and rewards
digging for the actual signal.

**A strong approach:**
1. Treats `recall@1 = 100%` as worth a second look before touching code —
   not because it's necessarily wrong, but because a perfect score on a
   brand-new eval deserves scrutiny.
2. Diffs `eval_set.json` against `policies.json` and notices queries are
   verbatim substrings of the docs, not independent phrasing.
3. Builds a small held-out set of paraphrased, realistic queries (not
   copy-pasted) and reruns — recall@1 stays 100%. Stopping here and
   concluding "no problem" misses it.
4. Digs further: surfaces retrieval confidence/distance (not currently
   exposed) and finds leaked queries sit measurably closer to their source
   docs than honest ones — the actual signature of the leak.
5. Explains the fix is about eval-set independence, not a code patch —
   `retriever.py`/`metrics.py` are both correct for what they claim to
   measure.
6. Verifies claims by actually running numbers, not by assertion.

**The extension (small new capability):** add a **confidence/abstention
threshold** — if the top result's distance is above a cutoff, return "no
confident policy match" instead of forcing a top-1 answer. Requires
surfacing the distance the retriever's ChromaDB query already computes
internally but currently discards (returns only `policy_id`s) — the real,
small code change — plus a `max_distance` param and extending the metric to
separate `recall_on_confident` from `abstention_rate` rather than folding
abstentions into either bucket. This is also the natural tool for finding
the leak in step 4 above, so a strong solution connects the two halves of
the exercise rather than treating them as unrelated. It also raises a second
discussion point: calibrating the threshold off the *leaky* eval set's
distances would silently produce a miscalibrated (too-tight) production
cutoff — a concrete instance of the "miscalibration" bug category above.

**Time budget against a 60 min slot:** 0–10 clone/orient (skippable here,
it's this repo) · 10–20 read eval script + metric, form leakage hypothesis ·
20–35 build held-out paraphrase set, notice recall doesn't drop, dig for the
real signal (distance) · 35–50 implement abstention extension + extend
metric · 50–60 verify + summarize tradeoffs.

**Built at `practice/policy_retrieval/`** (working files: `README.md`,
`policies.json`, `eval_set.json`, `retriever.py`, `metrics.py`, `eval.py`;
reference material under `solutions/`: `NOTES.md` with the verified numbers
and rubric, `generate_eval_set_leaky.py` + `generate_eval_set_fixed.py` for
reproducing both eval sets, `retriever_with_abstention.py` +
`metrics_with_abstention.py` as one worked reference for the extension). Run
with `python practice/policy_retrieval/eval.py`.

## Additional scenarios (for repeat reps, so the fix isn't memorized)

1. **Metric-only variant** — keep `eval_set.json` clean/independent; instead
   break `recall_at_k` itself so it checks substring containment of the
   policy *text* in the response rather than `policy_id` equality, so any
   non-empty retrieval "passes" regardless of relevance. Same "quietly wrong
   metric" pattern, no leakage.
2. **Train/test contamination variant** — apply the same idea to
   [rl_pipeline/offline_rl.py](rl_pipeline/offline_rl.py)'s
   `train_test_split(test_size=0.1, seed=42)` over ORPO triplets: templated
   trajectory summaries mean near-duplicate rows can land on both sides of
   the split. Different code shape (a real `train_test_split` call rather
   than a static eval set) — good for practicing the "pipeline" flavor of
   contamination instead of the "static eval set" flavor.
3. **Doc/code mismatch as a lighter warm-up** —
   [CLAUDE.md](CLAUDE.md) claims `VectorMemory` "powers the check_policy
   skill," but [skills/builtin/check_policy.py](skills/builtin/check_policy.py)
   never calls it and instead falls back to returning *all* policies when no
   keyword matches (`check_policy.py:45-46`), trivially inflating
   `compute_tool_correctness` recall. A concrete instance of the
   "agent/tool-calling" bug-category above. Smaller/faster than the primary
   scenario — good as a 20–30 min warm-up before a full 60-min run.

## Worked example: Escalation Predictor (classifier, label-derived leakage)

A second fully built practice ground, covering the "classifier" component
shape and a different flavor of leakage than the retrieval example above:
a feature only available *after* the outcome, rather than a corrupted eval
set.

**Framing:** a small classifier predicts whether a support ticket should be
routed to escalation specialists, from intake-time attributes (category,
priority, customer tier, body length). An `assigned_team` field is also
present in the training data — reused as a feature, it drives accuracy to
98.2%.

**The planted issue:** `assigned_team` is set by the real routing system
*after* the escalation decision is made — not something known at the moment
this prediction would actually need to run. It's a near-perfect encoding of
the label (97% agreement by construction). Removing it drops accuracy only
slightly (98.2% → 94.6%); the real tell is escalation-class **precision**
(1.00 → 0.71) — the leaky feature isn't improving recall at all, it's just
suppressing false positives by handing over the answer. Plain accuracy on
this ~11%-base-rate class is a weak signal on its own, which is itself a
second, smaller instance of the "metric quietly measuring the wrong thing"
category.

**The extension:** confidence-band abstention (predicted probability
0.35–0.65 routes to a human instead of forcing a call) — the same pattern
as the retrieval example's extension, applied to a classifier instead of a
retriever. Measured: `abstention_rate = 9.09%`,
`recall_on_confident = 0.6667`.

**Built at `practice/escalation_classifier/`** (working files: `README.md`,
`tickets.json`, `classifier.py` — a small hand-rolled logistic regression,
no `sklearn` dependency — `metrics.py`, `eval.py`; reference material under
`solutions/`: `NOTES.md` with the verified numbers, `generate_tickets.py`,
`eval_no_leak.py` as the worked fix + extension). Run with
`python practice/escalation_classifier/eval.py`.

## Practice-only scenario: Response Quality Judge (LLM-as-judge, no solution)

Planted, not fully worked — **no `solutions/` folder, no answer key.** Use
this one for real practice rather than as a reference; don't treat its
absence of a solution as an oversight.

**Framing:** a component uses a live call to the project's local Mistral
model to judge whether a generated support response adequately resolves a
ticket (`judge_pass_rate`, already wired up — one judge call per example,
trusted as the metric). 14 unlabeled `(ticket, response)` pairs, a mix of
genuinely adequate responses and ones with a subtler flaw (a wrong dollar
amount, an ignored second request, boilerplate that doesn't address an
urgent VIP escalation, a policy detail that contradicts the ticket's own
text) — deliberately not marked which is which.

**The planted issue category:** LLM-as-judge trustworthiness — a single run
is being treated as ground truth, with no check against independent human
judgment and no check on run-to-run stability. This is the category the
Format section above calls out explicitly; this is where it's actually
exercised end-to-end.

**Requires Ollama running locally** with `mistral:7b-instruct` pulled
(`docker-compose up -d`) — a real, disclosed dependency, not hidden. The
harness itself was smoke-tested against live Ollama to confirm it runs; the
pass rate it reports was deliberately not recorded anywhere, and no
reference fix/extension was built, so this stays a genuine unspoiled
exercise.

**Built at `practice/response_quality_judge/`**: `README.md`,
`tickets.json`, `judge.py`, `metrics.py`, `eval.py`. Run with
`python practice/response_quality_judge/eval.py`.
