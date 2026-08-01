"""Unit tests for MetaPlannerAgent's token-usage capture and runtime provider switching."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents.llm_client import LLMResponse
from agents.meta_planner import MetaPlannerAgent, _decompose_node
from a2a.capability_registry import CapabilityRegistry
from memory.per_agent_memory import PerAgentMemory


def _initial_state(category: str = "billing_dispute", body: str = "I was charged twice") -> dict:
    return {
        "ticket": {"category": category, "body": body, "priority": "medium"},
        "objective": "",
        "clarification_needed": False,
        "clarification_question": "",
        "plan_steps": [],
        "delegate_task": None,
        "delegate_inputs": {},
        "outcome": None,
        "notes": [],
    }


class TestDecomposeNodeTokenCapture:
    def test_captures_input_and_output_tokens(self):
        llm = MagicMock()
        llm.complete.return_value = LLMResponse(
            text='{"clarification_needed": false, "objective": "Resolve billing", '
                 '"delegate_to": "billing", "action_reason": "double charge"}',
            input_tokens=150,
            output_tokens=40,
        )
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 40

    def test_defaults_to_zero_when_llm_call_fails(self):
        llm = MagicMock()
        llm.complete.side_effect = ConnectionError("LLM provider unavailable")
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        # Fallback routing still happens even when the LLM is unreachable.
        assert result["delegate_task"] == "billing"

    def test_defaults_to_zero_when_response_has_no_counts(self):
        llm = MagicMock()
        llm.complete.return_value = LLMResponse(
            text='{"objective": "x", "delegate_to": "self"}', input_tokens=0, output_tokens=0,
        )
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0

    def test_tokens_do_not_affect_routing(self):
        llm = MagicMock()
        llm.complete.return_value = LLMResponse(
            text='{"clarification_needed": false, "objective": "Explain policy", '
                 '"delegate_to": "policy", "action_reason": "check refund window"}',
            input_tokens=90,
            output_tokens=25,
        )
        result = _decompose_node(_initial_state(category="policy_question", body="What is your refund window?"), llm)
        assert result["delegate_task"] == "policy"
        assert result["input_tokens"] == 90
        assert result["output_tokens"] == 25


@pytest.fixture
def agent_kwargs(tmp_path):
    return dict(
        registry=MagicMock(),
        shared_memory=MagicMock(),
        per_agent_memory=PerAgentMemory(db_path=tmp_path / "agents.db"),
    )


class TestProviderSwitch:
    def test_defaults_to_ollama_provider(self, agent_kwargs):
        agent = MetaPlannerAgent(capability_registry=CapabilityRegistry(), **agent_kwargs)
        assert agent.llm_provider == "ollama"

    def test_switch_provider_updates_llm_provider(self, agent_kwargs):
        agent = MetaPlannerAgent(capability_registry=CapabilityRegistry(), **agent_kwargs)
        agent.switch_provider("anthropic", api_key="sk-test")
        assert agent.llm_provider == "anthropic"

    def test_switch_provider_rejects_unknown_provider(self, agent_kwargs):
        agent = MetaPlannerAgent(capability_registry=CapabilityRegistry(), **agent_kwargs)
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            agent.switch_provider("openai")
        # Original provider is untouched on a failed switch.
        assert agent.llm_provider == "ollama"

    def test_switch_provider_is_picked_up_without_rebuilding_the_graph(self, agent_kwargs):
        """The decompose node closes over `self`, so swapping `self._llm` after
        construction must affect the next `.handle()`-driven decompose call —
        no `_build_graph()` call needed."""
        agent = MetaPlannerAgent(capability_registry=CapabilityRegistry(), **agent_kwargs)
        graph_before = agent._graph

        new_llm = MagicMock()
        new_llm.provider_name = "anthropic"
        new_llm.complete.return_value = LLMResponse(
            text='{"objective": "handled by new client", "delegate_to": "billing"}',
            input_tokens=10,
            output_tokens=5,
        )
        agent._llm = new_llm

        result = _decompose_node(_initial_state(), agent._llm)

        assert agent._graph is graph_before  # no rebuild happened
        assert new_llm.complete.called
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 5
