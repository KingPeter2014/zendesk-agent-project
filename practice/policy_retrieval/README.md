# Policy Answer Retrieval

A small policy-answering component. Given a customer query, it retrieves the
most relevant company policy from a short corpus using semantic search
(ChromaDB embeddings — the same style of retrieval used elsewhere in this
codebase's `VectorMemory`).

## Setup

`chromadb` is already a project dependency (see `pyproject.toml`), so no
extra install is needed if you've already run `pip install -e ".[dev]"` for
the main project.

```bash
python practice/policy_retrieval/eval.py
```

## What's here

- `policies.json` — the policy corpus (10 short policies).
- `eval_set.json` — labelled `(query, expected_policy_id)` pairs.
- `retriever.py` — `PolicyRetriever.retrieve(query, k)`, returns the top-k
  policy_ids for a query.
- `metrics.py` — `recall_at_k(eval_set, retriever, k)`, the metric already in
  place.
- `eval.py` — runs the eval set through the retriever and prints recall@k.

## Task (60 minutes)

1. **Find and fix an existing issue.** Run `eval.py`. Look at the reported
   recall@k. Is it trustworthy? Investigate, and fix whatever you find. The
   retrieval code and the metric code are not the only places a problem
   could live.
2. **Extend with a small new capability.** The retriever currently always
   returns its best guess, even when it isn't a good match. Give it a way
   to express "I'm not confident about this" instead of forcing an answer,
   and update the eval output to reflect that.

You're free to use AI tools — the interesting part is your real workflow:
how you prompt, how you verify what comes back, and when you choose to
write something by hand instead. Optimise for correctness and clear
reasoning about the data and the metric, not speed.
