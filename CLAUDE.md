# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

### Prerequisites
- Python 3.11+, Docker Desktop running
- Infrastructure: `docker-compose up -d` (starts Redis, Ollama, Jaeger, Prometheus, Grafana)
- Ollama pulls `mistral:7b-instruct` automatically (~4.1 GB)
- Generate synthetic data before first run: `python synthetic_data/ticket_generator.py`

### Entry Points
| What | Command |
|------|---------|
| Interactive UI | `streamlit run ui/app.py` → localhost:8501 |
| REST API | `uvicorn api/main:app --reload --port 8000` → docs at /docs |
| Headless demo (8 scenarios) | `python demo/run_demo.py` |
| Generate synthetic data | `python synthetic_data/ticket_generator.py` |

### Tests
```bash
pytest tests/ -v                              # all tests with 80% coverage enforcement
pytest tests/unit/ -v                         # unit tests only
pytest tests/integration/ -v                  # integration tests only
pytest tests/unit/test_memory.py -v           # single test module
```

Coverage is enforced at ≥80% via `--cov-fail-under=80` in `pyproject.toml`. HTML report at `htmlcov/index.html`. `meta_planner.py` and `offline_rl.py` are excluded from coverage (require live Ollama/model downloads).

### Environment
Copy `.env.example` to `.env`. Key variables: `REDIS_URL`, `OLLAMA_BASE_URL`, `OTLP_ENDPOINT`, `PROMETHEUS_PORT`, `API_PORT`.

`LLM_PROVIDER` selects the MetaPlanner's LLM backend at startup (`ollama` default, or `anthropic`
— requires `ANTHROPIC_API_KEY`, billed to that Anthropic account). Switchable at runtime without
a restart via the Streamlit sidebar or `PUT /config/llm-provider`; see `agents/llm_client.py`.

## Architecture Overview

This is a multi-agent customer support system. The data flow is:

```
User Ticket → [Input Guardrails] → MetaPlannerAgent → [Skill Execution Engine]
                                        ↓
                           BillingAgent / PolicyAgent / EscalationAgent
                                        ↓
                                [Output Guardrails] → Response
```

### Memory Architecture (Hybrid, 4 Layers)
- **SharedTicketState** (`memory/shared_memory.py`): Redis-backed ticket state with optimistic locking (`WATCH/MULTI/EXEC`) for concurrent agent safety — all agents coordinate through this.
- **WorkingMemory** (`memory/working_memory.py`): In-process, per-turn context accumulation and summarization.
- **PerAgentMemory** (`memory/per_agent_memory.py`): SQLite private store scoped per agent instance.
- **VectorMemory** (`memory/vector_memory.py`): ChromaDB for episodic memory (past resolved cases) and policy retrieval. Powers the `check_policy` skill.
- **All Pydantic schemas** live in `memory/models.py` — this is the single source of truth for `Ticket`, `Customer`, `Order`, `Plan`, `Trajectory`, `EvalMetrics`, etc.

### Agent Architecture
- **MetaPlannerAgent** (`agents/meta_planner.py`): Orchestrator. Uses LangGraph `StateGraph` + Ollama Mistral 7B-Instruct to produce a multi-step `Plan`, then delegates to specialist agents or executes skills directly.
- **Specialist Agents** (`agents/billing_agent.py`, `agents/policy_agent.py`, `agents/escalation_agent.py`): Receive `DelegationRequest` from the MetaPlanner via the A2A protocol.
- **BaseAgent** (`agents/base_agent.py`): Abstract class all agents inherit; defines `handle()` and `handle_delegation()` interfaces.
- **SupervisorAgent** (`agents/supervisor_agent.py`): Coordinates concurrent multi-agent workflows.

### Skills Layer
- **SkillRegistry** (`skills/registry.py`): Manages skill metadata, gating (disabled/experimental/stable), promotion thresholds, and pruning of unused synthesized skills.
- **ExecutionEngine** (`skills/execution_engine.py`): Executes `Plan` steps with exponential backoff retry and latency tracking.
- **5 Built-in Skills** (`skills/builtin/`): `lookup_order`, `process_refund`, `check_policy`, `escalate_ticket`, `send_notification`.

### A2A Delegation Protocol
`a2a/protocol.py` handles timeouts and error propagation. `a2a/capability_registry.py` maps `task_types → agent handlers`. `a2a/contracts.py` defines `DelegationContract` and `DelegationResult`.

### Guardrails
- **Input** (`guardrails/input_guardrails.py`): Prompt injection detection, PII redaction (regex + Presidio patterns). Runs before any LLM call.
- **Output** (`guardrails/output_guardrails.py`): Email/CC scrubbing, hallucination detection. Runs on all agent responses.
- **Governance** (`guardrails/governance.py`): Goal alignment checks, approval workflow for high-value refunds.

### Evaluation
- **EvaluationHarness** (`evaluation/harness.py`): Runs 11 scenarios → layered metrics.
- **Regression Gate** (`evaluation/regression_gate.py`): CI fails if any metric drops >5% vs baseline. Run by `.github/workflows/ci.yml`.
- **Scenarios**: `happy_path.py` (4), `adversarial.py` (3, prompt injection/PII attacks), `edge_cases.py` (4), `off_topic.py` (2).

### RL Pipeline
- `rl_pipeline/trajectory_logger.py`: Logs agent trajectories to SQLite for offline training.
- `rl_pipeline/reward_functions.py`: Composite reward (resolution success, efficiency, latency, error penalties).
- `rl_pipeline/offline_rl.py`: ORPO fine-tuning on Qwen2.5-0.5B via Hugging Face TRL (excluded from CI).

### Observability
- OpenTelemetry → Jaeger (traces): `observability/tracing.py`
- Prometheus + Grafana (metrics): `observability/metrics.py`, pre-built dashboard at `observability/dashboards/`
- Grafana at localhost:3000, Jaeger at localhost:16686, Prometheus at localhost:9090
