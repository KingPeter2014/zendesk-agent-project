# Eight‑Month Implementation Backlog

The following backlog outlines a high‑level plan to design, implement and deploy Zendesk’s next‑generation agentic system over an eight‑month period.  Dates assume the project starts in late May 2026.

| Month | Focus | Key Activities |
|---|---|---|
| **Month 1 (Jun 2026)** | **Research & Detailed Design** |  
• Perform deep literature survey on multi‑agent memory systems, offline RL for LLMs and agent evaluation; identify relevant open‑source libraries and frameworks.  
• Conduct stakeholder interviews (customer service teams, security, legal) to refine requirements and gather domain policies.  
• Finalise high‑level architecture and specify memory scoping rules, A2A protocol, skill gating criteria and guardrail categories.  
• Build a proof‑of‑concept of hybrid memory using an in‑memory database with versioning and transaction support. |
| **Month 2 (Jul 2026)** | **Memory & Skill Infrastructure** |  
• Implement the shared ticket memory service with concurrency control (optimistic locking, version numbers) and per‑agent stores.  
• Extend the existing skill registry to include metadata (preconditions, side‑effects, schema) and gating flags.  
• Create basic instrumentation for logging reads/writes to memory and skill usage statistics.  
• Develop an initial agent that uses the new memory layer to resolve simple tickets; run unit tests for concurrency and deduplication. |
| **Month 3 (Aug 2026)** | **Evaluation Harness & Quality Gates** |  
• Implement the evaluation harness with tracing to capture plan generation, tool calls and outcomes.  
• Define scenario‑based test cases: happy‑path, edge, adversarial and off‑topic.  
• Compute baseline metrics for existing agents (plan quality, tool correctness, task completion, latency).  
• Integrate the harness into CI/CD: on every commit, run tests and block deploys when metrics regress.  
• Start building dashboards for observability (metrics, cost, latency). |
| **Month 4 (Sep 2026)** | **Multi‑Agent Delegation & Supervisor** |  
• Define and implement the Agent‑to‑Agent (A2A) protocol: capability registry, delegation contracts, timeouts and escalation paths.  
• Implement specialised agents (e.g., BillingAgent, PolicyAgent, EscalationAgent) and test delegation on real ticket scenarios.  
• Create a supervisor agent that monitors execution, enforces guardrails (input/output filtering, least privilege) and mediates escalations.  
• Add context summarisation and clarification prompts for ambiguous tickets. |
| **Month 5 (Oct 2026)** | **RL Training Pipeline & Reward Modeling** |  
• Instrument the production system to log trajectories (user messages, plans, tool calls, outcomes) with anonymisation.  
• Define reward signals (resolution success, user satisfaction, efficiency) and implement reward shaping functions.  
• Build data pipelines to clean, label and batch trajectories for offline training.  
• Experiment with offline RL algorithms (OREO) on internal datasets; compare with DPO and supervised fine‑tuning.  
• Design evaluation metrics to compare candidate models using the harness. |
| **Month 6 (Nov 2026)** | **Model Training & Iterative Improvement** |  
• Train a small‑scale domain‑specialised model using offline RL; incorporate value functions and soft Bellman optimisation.  
• Run ablation studies on reward shaping and data filtering.  
• Deploy the candidate model in a sandbox environment and monitor performance; iterate on reward parameters and training hyper‑parameters.  
• Begin implementing online rollouts in simulation to supplement offline learning. |
| **Month 7 (Dec 2026)** | **System Integration & Guardrails** |  
• Integrate the trained model into the production agent architecture; update the planner to utilise new reasoning capabilities.  
• Implement black‑box guardrails (input/output filters) and guardrails by design (secure architecture, least privilege, monitoring).  
• Extend governance guardrails to detect goal misalignment and reward hacking; implement approval workflows for policy changes.  
• Expand the evaluation harness with safety tests (prompt injection resilience, bias detection). |
| **Month 8 (Jan 2027)** | **Hardening & Deployment** |  
• Conduct load and latency testing with thousands of concurrent sessions; optimise memory access patterns and caching.  
• Finalise skill gating policies and implement retention/pruning.  
• Provide internal training sessions for support teams and engineering on using the new system and interpreting evaluation metrics.  
• Conduct red‑team exercises to test guardrails and security posture.  
• Deploy the new agent architecture to production with feature flags; monitor key metrics and gradually increase traffic.  
• Publish a post‑mortem and plan for continuous improvement in 2027. |

This backlog emphasises concurrent work streams: core infrastructure, evaluation harness, RL training and safety/guardrails.  Activities may overlap, and feedback from early prototypes will inform later stages.