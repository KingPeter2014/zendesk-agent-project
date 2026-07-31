---
name: futuresecureai-interview-prep
description: "Use when preparing for or practicing a Future Secure AI Data Scientist (AI Engineer, Data Science) interview: live coding + repo walkthrough, solution design / evaluation / safety architecture whiteboard, or the BRAVER values interview. Also use to design or review practice scenarios (planted bugs, extension exercises, whiteboard prompts) against this repo as a stand-in codebase. Triggers: FutureSecureAI, Future Secure AI, BRAVER, CARL, data leakage, train/test contamination, LLM-as-judge, interview prep, mock interview, live coding interview, values interview."
---

# Future Secure AI — Data Scientist Interview Prep

Source: candidate-provided "Interview Prep Guide — Data Scientist (AI Engineer, Data Science)" (confidential, for candidate use). Three stages, ~2h15m total.

## Stage 1 — Live Coding & Repo Walkthrough (60 min)

Format: live pairing in a partially built repo (candidate gets it 10–15 min early to clone + confirm it runs). Not a puzzle/algorithm test.

- Codebase centres on a **model-driven component** (e.g. RAG answer component, text classifier) with a **small dataset** and a **metric already in place**.
- Task has two parts: **(a) find and fix an existing planted issue**, then **(b) extend the system with a small new capability**.
- Graded on correctness, reasoning about data/metric, and how the fix is *verified* — not speed.
- **Expect the planted issue to be one of:**
  - data leakage
  - train/test contamination
  - a metric that looks fine but is quietly measuring the wrong thing
- AI tools explicitly allowed and encouraged — they want to see the real workflow: how you prompt, how you verify the AI's output, and when you choose to hand-write instead.
- Assessed signal: statistical/evaluation fundamentals (leakage, metric choice, overfitting, sampling), clean/defensive coding, structured debugging, clear communication.
- If an LLM-as-judge is involved anywhere: be ready to justify why the judge is trustworthy — validate against human labels, check inter-rater agreement, and explain why one run / one score is not enough for a probabilistic system.

**Working method that matches what they're grading:**
1. Read the metric/eval code *before* touching the model/retrieval code — the bug is as likely to be in the metric as in the pipeline.
2. State a hypothesis out loud before changing anything ("this metric looks like it's rewarding X regardless of Y — let me check").
3. Write or run a test that isolates the bug before fixing it (red), then confirm the fix (green) — don't just eyeball the fix.
4. For the extension: keep it small and validate it against the *same* metric/eval path used for the fix, not a new ad hoc check.

## Stage 2 — Solution Design, Evaluation & Safety Architecture (45 min)

Format: whiteboard discussion, open-ended, no single correct answer. Centred on an open-ended real-world customer problem about data/model quality.

Graded on: problem framing, clean decomposition into components/agents, tradeoff reasoning, and — **specifically for this lane** — defining acceptance criteria and the evaluation *before* proposing the build.

- Ask more clarifying questions than feels natural before proposing a direction; a strong candidate asks more, not fewer.
- Structure an answer as: clarify the problem/users/constraints → define what "good" and "safe" mean *numerically* (the metric/acceptance bar) → decompose into components/agents → propose the architecture → call out tradeoffs and failure modes → describe how you'd know it regressed (regression gate / eval harness).
- Good to explicitly separate: task-quality metrics (did it solve the problem), safety metrics (did it do anything unsafe/off-policy), and efficiency metrics (cost/latency) — mirrors this repo's own layered eval design (see below).

## Stage 3 — Values Interview (30 min)

Behavioural, not technical. Structured around Future Secure AI's six **BRAVER** values:

- **Bold** — challenge the status quo, act on opportunities without complete certainty.
- **Rigorous** — hold a high bar, avoid shortcuts even when no one's watching.
- **Adaptable** — update your approach when new information comes in; stay steady when plans shift.
- **Valued** — understand what matters to customers/partners, balanced with what's sustainable.
- **Earnest** — communicate honestly, show genuine care in everyday interactions.
- **Relentless** — push through obstacles, add value beyond the minimum ask.

Prep: use **CARL** (Context → Action → Result → Learning; a STAR variant). Be specific about *your own* role, not the team's. Favour real examples about trade-offs, acting under uncertainty, or extra ownership — especially around data quality, model evaluation, or a metric that turned out to be misleading. Don't over-rehearse; they're evaluating how you think, not how you present.

## Using this repo as a practice ground

General principle: when asked to design or build a mock Stage 1 exercise against this repo, plant the issue as an isolated, clearly-labelled practice fixture (e.g. under a `practice/` directory with its own small dataset and metric) rather than silently corrupting the real production code — this repo is a live portfolio/CI project, not a scratch sandbox. Prefer planting the bug *in the data* (an eval set, a corpus) over a code bug where possible — that's harder to spot and closer to what "data leakage" actually looks like in practice.

### Primary Stage 1 scenario — Policy Answer Retrieval (RAG-shaped, data leakage)

Matches the guide almost exactly: "RAG answer component... with a small dataset and a metric already in place," planted issue = **data leakage**.

**Candidate-facing framing:** "Small policy-answering component. It retrieves the most relevant company policy for a customer query via semantic search over a policy corpus (reuses this repo's real [memory/vector_memory.py](memory/vector_memory.py) `VectorMemory.retrieve_policy`, backed by ChromaDB — genuine embedding retrieval, not the trivial keyword map in [skills/builtin/check_policy.py](skills/builtin/check_policy.py)). An eval script with a `recall_at_k` metric is already wired up and reports 100% recall@1. Investigate, then add [extension]."

**The dataset:**
- `policies.json` — ~10 short policy docs (reuse the 8 already seeded by `VectorMemory.seed_policies()` plus 2 more).
- `eval_set.json` — ~20 labelled `(query, expected_policy_id)` pairs.

**The metric already in place:** `recall_at_k(eval_set, retriever, k=1)` — fraction of queries where the expected policy_id is in the top-k retrieved results. Reports 100%.

**The planted issue (leakage, lives in the data, not the code):** `eval_set.json` was generated by taking verbatim substrings of the policy text itself as the "query" (e.g. policy *"Items can be returned within 30 days of delivery for a full refund."* → eval query *"returned within 30 days of delivery"*). Since the same embedding model embeds both documents and queries, and the query is literally a substring of the indexed document, cosine similarity is near-1.0 — recall@1 = 100% regardless of whether the retriever generalizes to real, paraphrased customer language at all. The eval set is not independent of the index it's scored against — classic data leakage, and it looks completely healthy until inspected.

**Important — verified empirically, don't assume:** an honestly paraphrased, independent eval set of the same 20 queries *also* scores `recall@1 = 100%` on this fixture (the 10-policy corpus is small and topically well-separated, so top-1 label accuracy is easy either way). The leak does **not** reveal itself as a recall drop. The real, measured tell is retrieval *confidence*: leaked queries sit unrealistically close to their source documents (mean top-1 distance 0.256) versus honest paraphrases (mean 0.394) — a real, ~54%-higher gap — but that distance is never surfaced by the retriever as given. This is a better exercise than a simple recall-drop would have been: it punishes candidates who stop at "recall didn't change, so it's fine" and rewards ones who dig for the actual signal.

**What a good candidate does:**
1. Treats `recall@1 = 100%` as worth a second look before touching code (matches the guide's "statistical fundamentals" signal) — not because it's necessarily wrong, but because a perfect score on a brand-new eval deserves scrutiny.
2. Diffs `eval_set.json` against `policies.json` and notices queries are verbatim substrings of the docs, not independent customer phrasing.
3. Builds a small held-out set of paraphrased, realistic queries (not copy-pasted) and reruns — recall@1 stays 100%. A candidate who stops here and concludes "no problem" has missed it.
4. Digs further: surfaces retrieval confidence/distance (not currently exposed) and finds leaked queries sit measurably closer to their source docs than honest ones — the actual signature of the leak.
5. Explains the fix is about eval-set independence, not a code patch — `retriever.py`/`metrics.py` are both correct for what they claim to measure.
6. Verifies claims by actually running numbers, not by assertion.

**The extension (small new capability):** add a **confidence/abstention threshold** — if the top result's distance is above a cutoff, return "no confident policy match" instead of forcing a top-1 answer. Requires surfacing the distance the retriever's ChromaDB query already computes internally but currently discards (returns only `policy_id`s) — the real, small code change — plus a `max_distance` param and extending the metric to separate `recall_on_confident` from `abstention_rate` rather than folding abstentions into either bucket. This is also the natural tool for finding the leak in step 4 above, so a strong candidate connects the two halves of the exercise rather than treating them as unrelated. Ties directly into Stage 2's safety framing (why a support bot should say "I don't know" rather than confidently guess), and into a second discussion point: calibrating the threshold off the *leaky* eval set's distances would silently produce a miscalibrated (too-tight) production cutoff.

**Time budget against the guide's 60 min:** 0–10 clone/orient (skippable here, it's this repo) · 10–20 read eval script + metric, form leakage hypothesis · 20–35 build held-out paraphrase set, notice recall doesn't drop, dig for the real signal (distance) · 35–50 implement abstention extension + extend metric · 50–60 verify + summarize tradeoffs.

**Built at `practice/policy_retrieval/`** (candidate-facing: `README.md`, `policies.json`, `eval_set.json`, `retriever.py`, `metrics.py`, `eval.py`; interviewer/self-check-facing under `solutions/`: `NOTES.md` with the verified numbers and rubric, `generate_eval_set_leaky.py` + `generate_eval_set_fixed.py` for reproducing both eval sets, `retriever_with_abstention.py` + `metrics_with_abstention.py` as one worked reference for the extension). Run with `python practice/policy_retrieval/eval.py`.

### Alternate variants (for repeat reps, so the fix isn't memorized)

1. **Metric-only variant** — keep `eval_set.json` clean/independent; instead break `recall_at_k` itself so it checks substring containment of the policy *text* in the response rather than `policy_id` equality, so any non-empty retrieval "passes" regardless of relevance. Same "quietly wrong metric" pattern, no leakage.
2. **Train/test contamination variant** — apply the same idea to [rl_pipeline/offline_rl.py](rl_pipeline/offline_rl.py)'s `train_test_split(test_size=0.1, seed=42)` over ORPO triplets: templated trajectory summaries mean near-duplicate rows can land on both sides of the split. Different code shape (a real `train_test_split` call rather than a static eval set) — good for practicing the "trainer/pipeline" flavor of contamination instead of the "static eval set" flavor.
3. **Doc/code mismatch as a lighter warm-up** — [CLAUDE.md](CLAUDE.md) claims `VectorMemory` "powers the check_policy skill," but [skills/builtin/check_policy.py](skills/builtin/check_policy.py) never calls it and instead falls back to returning *all* policies when no keyword matches (`check_policy.py:45-46`), trivially inflating `compute_tool_correctness` recall. Smaller/faster than the primary scenario — good as a 20–30 min warm-up rep before a full 60-min run.
