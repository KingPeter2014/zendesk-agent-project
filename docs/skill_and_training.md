# Human and Agent Skill Development

Deploying and maintaining Zendesk’s autonomous customer‑service agents requires a combination of human expertise and machine skills.  This document outlines the learning requirements for the engineering team and the capabilities that must be built into the agents themselves.

## Human Learning Requirements

### 1. Reinforcement Learning for Language Models

Engineers must understand the principles of offline and online reinforcement learning (RL), specifically as applied to large language models.  Offline RL methods like OREO jointly learn a policy and value function using the soft Bellman equation and require only logged trajectories rather than paired preference data【521210494030547†L16-L38】.  Team members should be comfortable with reward shaping, credit assignment, and the trade‑offs between offline and online RL (cost, exploration vs exploitation, risk of overfitting).

**Recommended actions:**

* Complete internal workshops on RL basics (Markov decision processes, soft Bellman equations, policy/value networks).  
* Study recent papers on offline RL for LLMs (OREO) and preference optimisation to understand limitations of DPO and PPO【521210494030547†L16-L38】.  
* Experiment with small‑scale RL pipelines using open datasets (e.g., GSM8K) to familiarise with training loops and evaluation.

### 2. Memory Engineering and Multi‑Agent Systems

As the mem0 analysis notes, multi‑agent memory is the hardest problem—36.9 % of failures are caused by inter‑agent misalignment【429630307714251†L64-L69】.  Engineers must learn to design hybrid memory architectures, define scoping rules (user, session, agent, application) and implement concurrency control to avoid duplication and inconsistent state【429630307714251†L78-L81】.  

**Recommended actions:**

* Review the CoALA framework for single‑agent memory (working vs long‑term memory, semantic/procedural knowledge)【429630307714251†L90-L101】 and extend it to multi‑agent settings.  
* Build prototypes with centralised, distributed and hybrid memory patterns to understand trade‑offs in latency and consistency【429630307714251†L69-L72】.  
* Learn concurrency control mechanisms (optimistic/pessimistic locking, versioning, CRDTs) and apply them to shared context stores.

### 3. Agent Evaluation and Quality Gates

Agent evaluation differs from traditional LLM evaluation; it must track the entire reasoning chain and action sequence.  Braintrust’s framework stresses layered metrics: plan quality, plan adherence, tool selection accuracy, tool correctness, execution path validity, task completion and safety【482633023112309†L69-L77】【482633023112309†L94-L110】.  Engineers must design and implement evaluation harnesses and integrate them into CI/CD.

**Recommended actions:**

* Study layered evaluation metrics and implement test harnesses with tracing to capture intermediate decisions【482633023112309†L173-L179】.  
* Develop scenario‑based test suites using real ticket data.  Include happy‑path, edge, adversarial and off‑topic cases【482633023112309†L155-L167】.  
* Integrate evaluation runs into continuous integration so that deployments are blocked when metrics regress.

### 4. Guardrails, Security and Policy Compliance

Engineers must understand the threat surface for autonomous agents and implement layered guardrails.  Black‑box guardrails filter inputs and outputs to block harmful prompts and PII and to detect hallucinations【732948394346663†L174-L186】.  Guardrails by design embed security into the architecture, apply the principle of least privilege, and integrate monitoring【732948394346663†L203-L224】.  Governance guardrails prevent goal misalignment and reward hacking【732948394346663†L252-L273】.  

**Recommended actions:**

* Learn to implement input/output filters, PII detection and toxicity/hallucination detectors.  
* Design systems with least‑privilege access control and role‑based permissions.  
* Build monitoring dashboards that track prompt and model versions, detect drift and log guardrail interventions.  
* Participate in red‑team exercises to test prompt injection resilience.

### 5. Multi‑Agent Delegation and A2A Protocols

Developers must design and implement the agent‑to‑agent (A2A) delegation protocol.  This includes capability advertisement, delegation contracts (inputs, expected outputs, error codes), timeouts and escalation paths.  The protocol must operate on shared memory pointers to avoid full context dumping and token bloat【429630307714251†L160-L167】.

### 6. Domain Expertise

Although the models can learn from data, human expertise in customer service workflows (refunds, order modifications, escalations) is vital.  Engineers should collaborate with customer‑service professionals to translate policies into structured skills and reward signals.

## Agent Skills Required

### Planning and Problem Decomposition

* **Hierarchical goal decomposition:** break ambiguous tickets into sub‑tasks, recognise when to ask clarifying questions and adjust plans accordingly.
* **Skill selection:** choose appropriate skills for sub‑tasks based on metadata (preconditions, side‑effects) and past success.
* **Plan refinement:** revise plans when actions fail or environment changes.

### Memory Interaction

* **Context retrieval:** fetch relevant information from working memory, long‑term memory and shared ticket memory.  Use summarisation to fit context into context windows.
* **Atomic updates:** write updates to shared memory using transactions and respect version checks to prevent race conditions.
* **Memory scoping:** read only the information relevant to the agent’s role and task.

### Tool Use and Execution

* **API invocation:** construct valid API requests, validate parameters and handle responses or errors.
* **Retry and backoff:** handle transient failures gracefully and avoid infinite loops.
* **Result interpretation:** parse responses and update internal state accordingly.

### Meta‑Reasoning and Self‑Evaluation

* **Plan adherence monitoring:** check whether execution follows the plan and decide when to replan.
* **Uncertainty estimation:** estimate confidence in outputs and flag uncertain results for human review.
* **Policy compliance:** ensure actions respect customer policies, company rules and legal requirements.  Defer to the **PolicyAgent** when uncertain.

### Collaboration and Delegation

* **Capability advertisement and discovery:** expose the skills each agent can perform and discover other agents’ capabilities.
* **Contract negotiation:** agree on input/output schemas, deadlines and failure handling.
* **Result hand‑off:** write results to shared memory, signal completion and transfer control back to the delegating agent.

### Safety and Security Awareness

* **Prompt injection detection:** recognise and ignore malicious or irrelevant instructions embedded in user text or tool outputs【732948394346663†L174-L181】.
* **Guardrail compliance:** adhere to input/output filters and respect least‑privilege access.  Escalate tasks that require permissions beyond the agent’s scope.
* **Bias and hallucination mitigation:** apply filters and cross‑check facts when generating content; abstain or ask for help when uncertain【732948394346663†L294-L301】.

### Learning and Adaptation

* **Skill learning:** synthesise new skills from successful traces while respecting gating criteria.
* **Continuous improvement:** feed execution traces into the RL training pipeline; adjust behaviour based on updated policy/value networks and new reward signals.

By investing in both human expertise and agent capabilities, Zendesk can build a robust agentic system that not only automates customer service tasks but continuously learns, adapts and operates safely at enterprise scale.