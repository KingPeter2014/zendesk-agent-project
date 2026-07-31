"""Unit tests for MetaPlannerAgent's token-usage capture at the Ollama call site."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.outputs import Generation, LLMResult

from agents.meta_planner import _decompose_node


def _fake_llm_result(text: str, prompt_eval_count: int | None = None,
                      eval_count: int | None = None) -> LLMResult:
    info: dict = {}
    if prompt_eval_count is not None:
        info["prompt_eval_count"] = prompt_eval_count
    if eval_count is not None:
        info["eval_count"] = eval_count
    return LLMResult(generations=[[Generation(text=text, generation_info=info)]])


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
        llm.generate.return_value = _fake_llm_result(
            '{"clarification_needed": false, "objective": "Resolve billing", '
            '"delegate_to": "billing", "action_reason": "double charge"}',
            prompt_eval_count=150,
            eval_count=40,
        )
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 40

    def test_defaults_to_zero_when_llm_call_fails(self):
        llm = MagicMock()
        llm.generate.side_effect = ConnectionError("Ollama unavailable")
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        # Fallback routing still happens even when the LLM is unreachable.
        assert result["delegate_task"] == "billing"

    def test_defaults_to_zero_when_generation_info_missing_counts(self):
        llm = MagicMock()
        llm.generate.return_value = _fake_llm_result('{"objective": "x", "delegate_to": "self"}')
        result = _decompose_node(_initial_state(), llm)
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0

    def test_tokens_do_not_affect_routing(self):
        llm = MagicMock()
        llm.generate.return_value = _fake_llm_result(
            '{"clarification_needed": false, "objective": "Explain policy", '
            '"delegate_to": "policy", "action_reason": "check refund window"}',
            prompt_eval_count=90,
            eval_count=25,
        )
        result = _decompose_node(_initial_state(category="policy_question", body="What is your refund window?"), llm)
        assert result["delegate_task"] == "policy"
        assert result["input_tokens"] == 90
        assert result["output_tokens"] == 25
