# Response Quality Judge

A small component that uses an LLM to judge whether a generated support response adequately resolves a customer's ticket. This one is for genuine, unspoiled practice — **there is no `solutions/` folder or answer key for this scenario.**

## Setup

Requires Ollama running locally with `mistral:7b-instruct` pulled (the same model the rest of this project uses):

```bash
docker-compose up -d
# wait until `docker-compose logs ollama` shows the model loaded
```

`langchain-ollama` is already a project dependency.

```bash
python practice/response_quality_judge/eval.py
```

## What's here

- `tickets.json` — 14 `(ticket_body, response)` pairs. No labels.
- `judge.py` — `LLMJudge.judge(ticket_body, response) -> "PASS" | "FAIL"`,
  a single live call to the local Mistral model per invocation.
- `metrics.py` — `judge_pass_rate(eval_set, judge)`, the metric already in place: the fraction of responses the judge rates PASS, based on one run per example.
- `eval.py` — runs the eval set through the judge and prints the pass rate.

## Task (45–60 minutes)

1. **Find and fix an existing issue.** Run `eval.py` a few times. Look at the reported `judge_pass_rate`. Is a single LLM call, run once per example, something you'd trust as ground truth for a quality metric?
   What would you actually check to find out? (The judge and metric code
   are both doing exactly what they claim to do — that doesn't mean the
   number they produce is trustworthy.)
2. **Extend with a small new capability.** The judge currently forces a
   single PASS/FAIL verdict from one run, with no way to express
   uncertainty. Give it a way to do that instead, and update the eval
   output to reflect it.

Optimise for correctness and clear reasoning about the judge and the
metric, not speed. AI tools are fine to use — the interesting part is your
real workflow: how you prompt, how you verify what comes back, and when you
choose to write something by hand instead.
