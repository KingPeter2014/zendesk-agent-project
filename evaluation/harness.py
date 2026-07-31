"""Evaluation harness: runs scenario suites and produces layered metric reports."""

from __future__ import annotations

import time
import uuid
from typing import Any

from memory.models import (
    EvalMetrics, EvalReport, OutcomeType,
    Ticket, TicketCategory, TicketPriority, TicketStatus,
)
from memory.shared_memory import SharedTicketMemory
from memory.models import SharedTicketState
from evaluation.metrics import evaluate_trajectory
from evaluation.scenarios.happy_path import Scenario


class EvaluationHarness:
    """
    Runs evaluation scenarios against a live agent system.
    Returns an EvalReport with all layered metrics.
    """

    def __init__(
        self,
        shared_memory: SharedTicketMemory,
        guardrail_checker: Any | None = None,
    ) -> None:
        self._shared_memory = shared_memory
        self._guardrail_checker = guardrail_checker

    def run_scenario(self, scenario: Scenario, agent: Any) -> EvalMetrics:
        ticket = Ticket(
            ticket_id=str(uuid.uuid4()),
            customer_id=str(uuid.uuid4()),
            order_id=scenario.context.get("order_id"),
            category=TicketCategory(scenario.ticket_category),
            priority=TicketPriority(scenario.ticket_priority),
            status=TicketStatus.OPEN,
            subject=scenario.ticket_subject,
            body=scenario.ticket_body,
        )

        # Initialise shared memory for this ticket
        state = SharedTicketState(ticket_id=ticket.ticket_id, ticket=ticket)
        if not self._shared_memory.exists(ticket.ticket_id):
            self._shared_memory.create(state)

        # Run input guardrail check
        guardrail_triggered = False
        if self._guardrail_checker is not None:
            check = self._guardrail_checker.check_input(ticket.body, ticket_id=ticket.ticket_id)
            if check.get("blocked"):
                from memory.models import Trajectory
                blocked_traj = Trajectory(
                    ticket_id=ticket.ticket_id,
                    agent_id="guardrail",
                    outcome=OutcomeType.BLOCKED,
                )
                return evaluate_trajectory(
                    blocked_traj,
                    scenario.scenario_id,
                    [],
                    0,
                    "guardrail block",
                    guardrail_triggered=True,
                )
            if check.get("pii_detected"):
                guardrail_triggered = True

        # Run agent
        start = time.perf_counter()
        trajectory = agent.handle(ticket, context=scenario.context)
        elapsed_ms = (time.perf_counter() - start) * 1000
        trajectory.total_latency_ms = elapsed_ms

        return evaluate_trajectory(
            trajectory,
            scenario.scenario_id,
            scenario.expected_tools,
            scenario.optimal_steps,
            scenario.name,
            guardrail_triggered=guardrail_triggered,
        )

    def run_suite(self, scenarios: list[Scenario], agent: Any) -> EvalReport:
        report = EvalReport()
        for scenario in scenarios:
            try:
                metrics = self.run_scenario(scenario, agent)
            except Exception as exc:
                from memory.models import Trajectory
                fallback_traj = Trajectory(
                    ticket_id="error",
                    agent_id="harness",
                    outcome=OutcomeType.FAILED,
                )
                metrics = evaluate_trajectory(
                    fallback_traj,
                    scenario.scenario_id,
                    scenario.expected_tools,
                    scenario.optimal_steps,
                    scenario.name,
                )
                metrics.plan_quality = 0.0
            report.scenario_results.append(metrics)
        return report

    def print_report(self, report: EvalReport) -> None:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"Evaluation Report [{report.run_id[:8]}]")
        table.add_column("Scenario", style="cyan")
        table.add_column("Plan Q", justify="right")
        table.add_column("Tool Corr", justify="right")
        table.add_column("Complete", justify="center")
        table.add_column("Efficiency", justify="right")
        table.add_column("Safety", justify="right")
        table.add_column("Latency ms", justify="right")
        table.add_column("In Tok", justify="right")
        table.add_column("Out Tok", justify="right")
        table.add_column("Total Tok", justify="right")
        table.add_column("Cost $", justify="right")
        table.add_column("Outcome", style="green")

        for r in report.scenario_results:
            table.add_row(
                r.scenario_id,
                f"{r.plan_quality:.2f}",
                f"{r.tool_correctness:.2f}",
                "✓" if r.task_completion else "✗",
                f"{r.step_efficiency:.2f}",
                f"{r.safety_score:.2f}",
                f"{r.latency_ms:.0f}",
                f"{r.input_tokens}",
                f"{r.output_tokens}",
                f"{r.total_tokens}",
                f"{r.cost_usd:.4f}",
                r.outcome.value if r.outcome else "—",
            )

        console.print(table)
        console.print(f"\n[bold]Aggregate:[/bold] plan_quality={report.avg_plan_quality:.2f}  "
                      f"tool_correctness={report.avg_tool_correctness:.2f}  "
                      f"completion={report.task_completion_rate:.0%}  "
                      f"safety={report.avg_safety_score:.2f}  "
                      f"latency={report.avg_latency_ms:.0f}ms  "
                      f"tokens={report.total_tokens_used} "
                      f"(in={report.total_input_tokens}, out={report.total_output_tokens})  "
                      f"cost=${report.total_cost_usd:.4f}")
