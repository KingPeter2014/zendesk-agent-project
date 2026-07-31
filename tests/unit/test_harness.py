"""Unit tests for EvaluationHarness and scenario definitions."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from memory.models import (
    AgentRole, AgentStep, OutcomeType, SharedTicketState,
    Ticket, TicketCategory, TicketPriority, TicketStatus, Trajectory, ToolCall,
)
from memory.shared_memory import SharedTicketMemory
from evaluation.harness import EvaluationHarness
from evaluation.scenarios.happy_path import HAPPY_PATH_SCENARIOS, Scenario
from evaluation.scenarios.adversarial import ADVERSARIAL_SCENARIOS
from evaluation.scenarios.edge_cases import EDGE_CASE_SCENARIOS
from evaluation.scenarios.off_topic import OFF_TOPIC_SCENARIOS
from guardrails.input_guardrails import InputGuardrails


@pytest.fixture
def mock_shared_memory():
    mock = MagicMock(spec=SharedTicketMemory)
    mock.exists.return_value = False
    mock.create.return_value = None
    return mock


@pytest.fixture
def mock_agent():
    def _handle(ticket, context=None):
        step = AgentStep(
            agent_id="test",
            agent_role=AgentRole.BILLING,
            action="execute:lookup_order",
        )
        step.tool_calls.append(ToolCall(tool_name="lookup_order", inputs={}))
        return Trajectory(
            ticket_id=ticket.ticket_id,
            agent_id="test",
            outcome=OutcomeType.RESOLVED,
            steps=[step],
            total_latency_ms=100.0,
        )
    agent = MagicMock()
    agent.handle.side_effect = _handle
    return agent


class TestScenarioDefinitions:
    def test_happy_path_scenarios_not_empty(self):
        assert len(HAPPY_PATH_SCENARIOS) > 0

    def test_happy_path_scenario_fields(self):
        s = HAPPY_PATH_SCENARIOS[0]
        assert s.scenario_id
        assert s.ticket_body
        assert s.ticket_subject

    def test_adversarial_scenarios_not_empty(self):
        assert len(ADVERSARIAL_SCENARIOS) > 0

    def test_adversarial_contains_injection(self):
        bodies = [s.ticket_body for s in ADVERSARIAL_SCENARIOS]
        assert any("ignore" in b.lower() or "system" in b.lower() for b in bodies)

    def test_edge_case_scenarios_not_empty(self):
        assert len(EDGE_CASE_SCENARIOS) > 0

    def test_off_topic_scenarios_not_empty(self):
        assert len(OFF_TOPIC_SCENARIOS) > 0

    def test_scenario_defaults(self):
        s = Scenario(
            scenario_id="test",
            name="Test",
            ticket_category=TicketCategory.BILLING_DISPUTE.value,
            ticket_priority=TicketPriority.MEDIUM.value,
            ticket_body="Test body",
            ticket_subject="Test subject",
        )
        assert s.optimal_steps == 2
        assert s.expected_outcome == "resolved"
        assert s.context == {}
        assert s.expected_tools == []


class TestEvaluationHarness:
    def test_run_scenario_resolved(self, mock_shared_memory, mock_agent):
        harness = EvaluationHarness(mock_shared_memory)
        metrics = harness.run_scenario(HAPPY_PATH_SCENARIOS[0], mock_agent)
        assert metrics.task_completion is True

    def test_run_scenario_creates_shared_memory_entry(self, mock_shared_memory, mock_agent):
        harness = EvaluationHarness(mock_shared_memory)
        harness.run_scenario(HAPPY_PATH_SCENARIOS[0], mock_agent)
        mock_shared_memory.create.assert_called_once()

    def test_run_scenario_skips_create_if_exists(self, mock_shared_memory, mock_agent):
        mock_shared_memory.exists.return_value = True
        harness = EvaluationHarness(mock_shared_memory)
        harness.run_scenario(HAPPY_PATH_SCENARIOS[0], mock_agent)
        mock_shared_memory.create.assert_not_called()

    def test_run_scenario_guardrail_blocks_injection(self, mock_shared_memory, mock_agent):
        guardrails = InputGuardrails()
        harness = EvaluationHarness(mock_shared_memory, guardrail_checker=guardrails)
        injection_scenario = ADVERSARIAL_SCENARIOS[0]
        metrics = harness.run_scenario(injection_scenario, mock_agent)
        assert metrics.outcome == OutcomeType.BLOCKED

    def test_run_scenario_pii_flagged_but_not_blocked(self, mock_shared_memory, mock_agent):
        guardrails = InputGuardrails()
        harness = EvaluationHarness(mock_shared_memory, guardrail_checker=guardrails)
        pii_scenario = ADVERSARIAL_SCENARIOS[2]
        metrics = harness.run_scenario(pii_scenario, mock_agent)
        assert metrics.outcome == OutcomeType.RESOLVED

    def test_run_suite_all_scenarios(self, mock_shared_memory, mock_agent):
        harness = EvaluationHarness(mock_shared_memory)
        report = harness.run_suite(HAPPY_PATH_SCENARIOS, mock_agent)
        assert len(report.scenario_results) == len(HAPPY_PATH_SCENARIOS)

    def test_run_suite_handles_agent_exception(self, mock_shared_memory):
        failing_agent = MagicMock()
        failing_agent.handle.side_effect = RuntimeError("Agent exploded")
        harness = EvaluationHarness(mock_shared_memory)
        report = harness.run_suite([HAPPY_PATH_SCENARIOS[0]], failing_agent)
        assert len(report.scenario_results) == 1
        assert report.scenario_results[0].plan_quality == 0.0
        assert report.scenario_results[0].outcome == OutcomeType.FAILED

    def test_run_suite_empty_returns_empty_report(self, mock_shared_memory, mock_agent):
        harness = EvaluationHarness(mock_shared_memory)
        report = harness.run_suite([], mock_agent)
        assert len(report.scenario_results) == 0

    def test_run_suite_mixed_scenarios(self, mock_shared_memory, mock_agent):
        all_scenarios = HAPPY_PATH_SCENARIOS + EDGE_CASE_SCENARIOS + OFF_TOPIC_SCENARIOS
        harness = EvaluationHarness(mock_shared_memory)
        report = harness.run_suite(all_scenarios, mock_agent)
        assert len(report.scenario_results) == len(all_scenarios)
