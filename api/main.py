"""FastAPI REST layer: submit tickets, retrieve state, expose metrics."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import BaseModel

from memory.models import (
    SharedTicketState, Ticket, TicketCategory, TicketPriority, TicketStatus,
)
from memory.shared_memory import SharedTicketMemory, VersionConflictError
from memory.per_agent_memory import PerAgentMemory
from skills.builtin.register import build_default_registry
from agents.meta_planner import MetaPlannerAgent
from agents.system_bootstrap import build_agent_graph
from a2a.capability_registry import CapabilityRegistry
from guardrails.input_guardrails import InputGuardrails
from observability.metrics import (
    agent_requests_total, agent_latency_seconds,
    guardrail_blocks_total, memory_version_conflicts_total,
    rl_trajectories_total, start_metrics_server,
)
from observability.tracing import get_tracer, init_tracing
from rl_pipeline.trajectory_logger import TrajectoryLogger
from rl_pipeline.reward_functions import score_trajectory

import time

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

shared_memory: SharedTicketMemory | None = None
per_agent_mem: PerAgentMemory | None = None
registry = None
capability_registry: CapabilityRegistry | None = None
meta_planner: MetaPlannerAgent | None = None
input_guardrails: InputGuardrails | None = None
trajectory_logger: TrajectoryLogger | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global shared_memory, per_agent_mem, registry, capability_registry
    global meta_planner, input_guardrails, trajectory_logger

    init_tracing()
    shared_memory = SharedTicketMemory()
    per_agent_mem = PerAgentMemory()
    registry = build_default_registry()
    input_guardrails = InputGuardrails()
    trajectory_logger = TrajectoryLogger()

    graph = build_agent_graph(registry, shared_memory, per_agent_mem, with_supervisor=False)
    capability_registry = graph["capability_registry"]
    meta_planner = graph["meta_planner"]

    start_metrics_server(8001)
    yield


app = FastAPI(title="Zendesk Agent API", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class TicketRequest(BaseModel):
    customer_id: str | None = None
    order_id: str | None = None
    category: str = TicketCategory.BILLING_DISPUTE.value
    priority: str = TicketPriority.MEDIUM.value
    subject: str
    body: str
    context: dict[str, Any] = {}


class TicketResponse(BaseModel):
    ticket_id: str
    outcome: str | None
    trajectory_id: str
    latency_ms: float
    guardrail_triggered: bool


class LLMProviderRequest(BaseModel):
    provider: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/ticket", response_model=TicketResponse)
def submit_ticket(request: TicketRequest):
    tracer = get_tracer()
    with tracer.start_as_current_span("api.submit_ticket") as span:
        span.set_attribute("ticket.category", request.category)
        span.set_attribute("ticket.priority", request.priority)

        # Guardrail check
        check = input_guardrails.check_input(request.body)  # type: ignore[union-attr]
        if check["blocked"]:
            span.set_attribute("guardrail.blocked", True)
            span.set_status(trace.StatusCode.ERROR, "blocked by input guardrail")
            guardrail_blocks_total.labels(guardrail_type="input", trigger="prompt_injection").inc()
            raise HTTPException(status_code=400, detail="Request blocked by input guardrail")

        ticket = Ticket(
            ticket_id=str(uuid.uuid4()),
            customer_id=request.customer_id or str(uuid.uuid4()),
            order_id=request.order_id,
            category=TicketCategory(request.category),
            priority=TicketPriority(request.priority),
            status=TicketStatus.OPEN,
            subject=request.subject,
            body=check["sanitised_text"],
        )
        span.set_attribute("ticket.id", ticket.ticket_id)

        state = SharedTicketState(ticket_id=ticket.ticket_id, ticket=ticket)
        shared_memory.create(state)  # type: ignore[union-attr]

        start = time.perf_counter()
        trajectory = meta_planner.handle(ticket, request.context)  # type: ignore[union-attr]
        elapsed = (time.perf_counter() - start) * 1000

        trajectory = score_trajectory(trajectory)
        trajectory_logger.log(trajectory)  # type: ignore[union-attr]
        rl_trajectories_total.inc()
        outcome = trajectory.outcome.value if trajectory.outcome else "unknown"
        span.set_attribute("trajectory.outcome", outcome)
        span.set_attribute("trajectory.latency_ms", elapsed)
        agent_requests_total.labels(
            agent_role="meta_planner",
            outcome=outcome,
        ).inc()
        agent_latency_seconds.labels(agent_role="meta_planner").observe(elapsed / 1000)

        return TicketResponse(
            ticket_id=ticket.ticket_id,
            outcome=trajectory.outcome.value if trajectory.outcome else None,
            trajectory_id=trajectory.trajectory_id,
            latency_ms=elapsed,
            guardrail_triggered=check.get("pii_detected", False),
        )


@app.get("/ticket/{ticket_id}")
def get_ticket(ticket_id: str):
    state = shared_memory.get(ticket_id)  # type: ignore[union-attr]
    if state is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return state.model_dump(mode="json")


@app.get("/skills")
def list_skills():
    return registry.stats()  # type: ignore[union-attr]


@app.get("/capabilities")
def list_capabilities():
    return [
        {"agent_id": c.agent_id, "role": c.agent_role, "task_types": c.task_types}
        for c in capability_registry.list_all()  # type: ignore[union-attr]
    ]


@app.get("/guardrail-events")
def guardrail_events():
    return [e.model_dump(mode="json") for e in input_guardrails.get_events()]  # type: ignore[union-attr]


@app.get("/config/llm-provider")
def get_llm_provider():
    return {"provider": meta_planner.llm_provider}  # type: ignore[union-attr]


@app.put("/config/llm-provider")
def set_llm_provider(request: LLMProviderRequest):
    try:
        meta_planner.switch_provider(request.provider)  # type: ignore[union-attr]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"provider": meta_planner.llm_provider}  # type: ignore[union-attr]


@app.get("/health")
def health():
    return {"status": "ok"}
