"""Execution engine: interprets a plan, invokes skills, retries on failure."""

from __future__ import annotations

import time
from typing import Any

from opentelemetry import trace
from tenacity import retry, stop_after_attempt, wait_exponential

from memory.models import AgentStep, AgentRole, Plan, PlanStep, ToolCall, Trajectory, OutcomeType
from memory.working_memory import WorkingMemory
from observability.tracing import get_tracer
from skills.registry import SkillRegistry


class SkillExecutionError(Exception):
    pass


class ExecutionEngine:

    def __init__(self, registry: SkillRegistry, agent_id: str, agent_role: AgentRole) -> None:
        self._registry = registry
        self._agent_id = agent_id
        self._agent_role = agent_role

    def execute(
        self,
        plan: Plan,
        working_memory: WorkingMemory,
        context: dict[str, Any] | None = None,
    ) -> Trajectory:
        trajectory = Trajectory(
            ticket_id=plan.ticket_id,
            agent_id=self._agent_id,
        )
        working_memory.set_plan(plan)
        completed_steps: dict[str, Any] = {}
        context = context or {}

        for plan_step in plan.steps:
            step = self._execute_step(plan_step, working_memory, completed_steps, context)
            trajectory.steps.append(step)
            if step.tool_calls and step.tool_calls[-1].error:
                trajectory.outcome = OutcomeType.FAILED
                break
            completed_steps[plan_step.step_id] = step

        if trajectory.outcome is None:
            trajectory.outcome = OutcomeType.RESOLVED

        trajectory.total_latency_ms = sum(
            tc.latency_ms
            for step in trajectory.steps
            for tc in step.tool_calls
        )
        return trajectory

    def _execute_step(
        self,
        plan_step: PlanStep,
        working_memory: WorkingMemory,
        completed: dict[str, Any],
        context: dict[str, Any],
    ) -> AgentStep:
        tracer = get_tracer()
        with tracer.start_as_current_span(f"skill.{plan_step.skill_name}") as span:
            agent_step = AgentStep(
                agent_id=self._agent_id,
                agent_role=self._agent_role,
                action=f"execute:{plan_step.skill_name}",
                reasoning=plan_step.rationale,
            )

            entry = self._registry.get(plan_step.skill_name)
            if entry is None:
                span.set_status(trace.StatusCode.ERROR, "skill not found in registry")
                tool_call = ToolCall(
                    tool_name=plan_step.skill_name,
                    inputs=plan_step.inputs,
                    error=f"Skill '{plan_step.skill_name}' not found in registry",
                )
                agent_step.tool_calls.append(tool_call)
                working_memory.record_tool_call(tool_call)
                return agent_step

            meta, fn = entry
            merged_inputs = {**context, **plan_step.inputs}

            start = time.perf_counter()
            output = None
            error = None
            try:
                output = self._invoke_with_retry(fn, merged_inputs)
                self._registry.record_invocation(plan_step.skill_name, success=True)
            except Exception as exc:
                error = str(exc)
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, error)
                self._registry.record_invocation(plan_step.skill_name, success=False)

            latency_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("skill.latency_ms", latency_ms)

            tool_call = ToolCall(
                tool_name=plan_step.skill_name,
                inputs=merged_inputs,
                output=output,
                error=error,
                latency_ms=latency_ms,
            )
            agent_step.tool_calls.append(tool_call)
            working_memory.record_tool_call(tool_call, result_key=plan_step.skill_name)
            return agent_step

    @staticmethod
    def _invoke_with_retry(fn, inputs: dict[str, Any], max_attempts: int = 3) -> Any:
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return fn(**inputs)
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    time.sleep(0.1 * (2 ** attempt))
        raise last_exc  # type: ignore[misc]
