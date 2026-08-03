"""Unit tests for the provider-agnostic LLM client abstraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.outputs import Generation, LLMResult

from agents.llm_client import AnthropicClient, OllamaClient, create_llm_client


def _fake_ollama_result(text: str, prompt_eval_count: int | None = None,
                         eval_count: int | None = None) -> LLMResult:
    info: dict = {}
    if prompt_eval_count is not None:
        info["prompt_eval_count"] = prompt_eval_count
    if eval_count is not None:
        info["eval_count"] = eval_count
    return LLMResult(generations=[[Generation(text=text, generation_info=info)]])


def _fake_anthropic_message(text: str, input_tokens: int, output_tokens: int) -> MagicMock:
    block = MagicMock(type="text", text=text)
    message = MagicMock()
    message.content = [block]
    message.usage.input_tokens = input_tokens
    message.usage.output_tokens = output_tokens
    return message


class TestOllamaClient:
    def test_complete_extracts_text_and_tokens(self):
        client = OllamaClient(model="mistral:7b-instruct", base_url="http://localhost:11434")
        client._llm = MagicMock()
        client._llm.generate.return_value = _fake_ollama_result(
            '{"objective": "x"}', prompt_eval_count=150, eval_count=40,
        )

        result = client.complete("some prompt")

        assert result.text == '{"objective": "x"}'
        assert result.input_tokens == 150
        assert result.output_tokens == 40

    def test_complete_defaults_to_zero_when_counts_missing(self):
        client = OllamaClient(model="mistral:7b-instruct", base_url="http://localhost:11434")
        client._llm = MagicMock()
        client._llm.generate.return_value = _fake_ollama_result('{"objective": "x"}')

        result = client.complete("some prompt")

        assert result.input_tokens == 0
        assert result.output_tokens == 0

    def test_provider_name(self):
        assert OllamaClient(model="m", base_url="http://x").provider_name == "ollama"


class TestAnthropicClient:
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicClient(api_key="", model="claude-haiku-4-5-20251001")

    @patch("agents.llm_client.anthropic.Anthropic")
    def test_complete_extracts_text_and_tokens(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_anthropic_message(
            '{"objective": "y"}', input_tokens=200, output_tokens=55,
        )
        mock_anthropic_cls.return_value = mock_client

        client = AnthropicClient(api_key="sk-test", model="claude-haiku-4-5-20251001")
        result = client.complete("some prompt")

        assert result.text == '{"objective": "y"}'
        assert result.input_tokens == 200
        assert result.output_tokens == 55
        mock_client.messages.create.assert_called_once()
        _, kwargs = mock_client.messages.create.call_args
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["messages"] == [{"role": "user", "content": "some prompt"}]

    @patch("agents.llm_client.anthropic.Anthropic")
    def test_provider_name(self, mock_anthropic_cls):
        client = AnthropicClient(api_key="sk-test", model="claude-haiku-4-5-20251001")
        assert client.provider_name == "anthropic"


class TestCreateLlmClient:
    def test_ollama_provider_returns_ollama_client(self):
        client = create_llm_client("ollama")
        assert isinstance(client, OllamaClient)

    @patch("agents.llm_client.anthropic.Anthropic")
    def test_anthropic_provider_returns_anthropic_client(self, mock_anthropic_cls):
        client = create_llm_client("anthropic", api_key="sk-test")
        assert isinstance(client, AnthropicClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client("openai")

    def test_overrides_take_precedence_over_config_defaults(self):
        client = create_llm_client("ollama", model="custom-model", base_url="http://custom:1234")
        assert client._model_name == "custom-model"
