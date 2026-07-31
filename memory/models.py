"""Core Pydantic schemas shared across the entire system."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TicketCategory(str, Enum):
    BILLING_DISPUTE = "billing_dispute"
    ORDER_ISSUE = "order_issue"
    POLICY_QUESTION = "policy_question"
    VIP_ESCALATION = "vip_escalation"
    OFF_TOPIC = "off_topic"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AWAITING_CUSTOMER = "awaiting_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AgentRole(str, Enum):
    META_PLANNER = "meta_planner"
    BILLING = "billing"
    POLICY = "policy"
    ESCALATION = "escalation"
    SUPERVISOR = "supervisor"


class OutcomeType(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLARIFICATION_NEEDED = "clarification_needed"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Synthetic domain objects
# ---------------------------------------------------------------------------

class Customer(BaseModel):
    customer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    tier: str = "standard"  # standard | premium | vip
    account_age_days: int = 0
    total_orders: int = 0
    lifetime_value: float = 0.0


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    product_name: str
    amount: float
    currency: str = "USD"
    status: str = "delivered"  # pending | processing | shipped | delivered | returned | refunded
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: datetime | None = None


class Ticket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    order_id: str | None = None
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    subject: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    csat_score: float | None = None  # 1–5


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    inputs: dict[str, Any] = {}
    expected_output_keys: list[str] = []
    depends_on: list[str] = []  # step_ids
    rationale: str = ""


class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    objective: str
    steps: list[PlanStep] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


# ---------------------------------------------------------------------------
# Execution trace
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    tool_name: str
    inputs: dict[str, Any]
    output: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_role: AgentRole
    action: str
    tool_calls: list[ToolCall] = []
    reasoning: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Trajectory(BaseModel):
    trajectory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    agent_id: str
    steps: list[AgentStep] = []
    outcome: OutcomeType | None = None
    reward: float | None = None
    total_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Shared ticket memory (Redis-backed)
# ---------------------------------------------------------------------------

class SharedTicketState(BaseModel):
    ticket_id: str
    version: int = 0
    ticket: Ticket
    plan: Plan | None = None
    active_agent: str | None = None
    assigned_agents: list[str] = []
    tool_results: dict[str, Any] = {}
    outcome: OutcomeType | None = None
    notes: list[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# A2A delegation
# ---------------------------------------------------------------------------

class DelegationContract(BaseModel):
    contract_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    delegating_agent: str
    target_agent_role: AgentRole
    shared_memory_ref: str  # ticket_id
    inputs: dict[str, Any] = {}
    expected_output_keys: list[str] = []
    timeout_s: float = 30.0
    fallback_action: str = "escalate"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DelegationResult(BaseModel):
    contract_id: str
    success: bool
    outputs: dict[str, Any] = {}
    error: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class EvalMetrics(BaseModel):
    scenario_id: str
    ticket_id: str
    plan_quality: float = 0.0         # 0–1, LLM-as-judge
    tool_correctness: float = 0.0     # fraction of expected tool calls made correctly
    task_completion: bool = False
    step_efficiency: float = 0.0      # optimal_steps / actual_steps (capped 0–1)
    latency_ms: float = 0.0
    safety_score: float = 1.0         # 1 = safe, 0 = guardrail fired
    outcome: OutcomeType | None = None


class EvalReport(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scenario_results: list[EvalMetrics] = []

    @property
    def avg_plan_quality(self) -> float:
        if not self.scenario_results:
            return 0.0
        return sum(r.plan_quality for r in self.scenario_results) / len(self.scenario_results)

    @property
    def avg_tool_correctness(self) -> float:
        if not self.scenario_results:
            return 0.0
        return sum(r.tool_correctness for r in self.scenario_results) / len(self.scenario_results)

    @property
    def task_completion_rate(self) -> float:
        if not self.scenario_results:
            return 0.0
        return sum(1 for r in self.scenario_results if r.task_completion) / len(self.scenario_results)

    @property
    def avg_latency_ms(self) -> float:
        if not self.scenario_results:
            return 0.0
        return sum(r.latency_ms for r in self.scenario_results) / len(self.scenario_results)

    @property
    def avg_safety_score(self) -> float:
        if not self.scenario_results:
            return 1.0
        return sum(r.safety_score for r in self.scenario_results) / len(self.scenario_results)


# ---------------------------------------------------------------------------
# Guardrail events
# ---------------------------------------------------------------------------

class GuardrailEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    guardrail_type: str  # input | output | governance
    trigger: str         # pii | prompt_injection | toxicity | hallucination | goal_misalignment
    severity: str = "medium"  # low | medium | high | critical
    original_text: str = ""
    action_taken: str = ""  # blocked | anonymized | flagged | approved
    ticket_id: str | None = None
    agent_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def pii_redacted(
        cls, guardrail_type: str, text: str, ticket_id: str | None = None, agent_id: str | None = None,
    ) -> "GuardrailEvent":
        """Build the event emitted when input/output PII is detected and anonymized."""
        return cls(
            guardrail_type=guardrail_type,
            trigger="pii",
            severity="high",
            original_text=text[:200],
            action_taken="anonymized",
            ticket_id=ticket_id,
            agent_id=agent_id,
        )
