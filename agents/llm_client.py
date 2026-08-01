"""Provider-agnostic LLM client abstraction.

Normalizes over two very different underlying interfaces — Ollama's legacy
LangChain `LLM.generate()` (text completion) and Anthropic's chat-style
`messages.create()` — so callers only ever deal with `.complete(prompt) -> LLMResponse`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import anthropic
from langchain_ollama import OllamaLLM

import config


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    provider_name: str

    def complete(self, prompt: str) -> LLMResponse: ...


class OllamaClient:
    provider_name = "ollama"

    def __init__(self, model: str, base_url: str, temperature: float = 0.1) -> None:
        self._model_name = model
        self._llm = OllamaLLM(model=model, base_url=base_url, temperature=temperature)

    def complete(self, prompt: str) -> LLMResponse:
        result = self._llm.generate([prompt])
        generation = result.generations[0][0]
        usage = generation.generation_info or {}
        return LLMResponse(
            text=generation.text,
            # Ollama's native response fields, surfaced via generation_info.
            input_tokens=usage.get("prompt_eval_count", 0),
            output_tokens=usage.get("eval_count", 0),
        )


class AnthropicClient:
    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024) -> None:
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set — required to use the anthropic LLM provider."
            )
        self._model_name = model
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str) -> LLMResponse:
        message = self._client.messages.create(
            model=self._model_name,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )


def create_llm_client(provider: str, **overrides: str) -> LLMClient:
    if provider == "ollama":
        return OllamaClient(
            model=overrides.get("model", config.OLLAMA_MODEL),
            base_url=overrides.get("base_url", config.OLLAMA_BASE_URL),
        )
    if provider == "anthropic":
        return AnthropicClient(
            api_key=overrides.get("api_key", config.ANTHROPIC_API_KEY),
            model=overrides.get("model", config.ANTHROPIC_MODEL),
        )
    raise ValueError(f"Unknown LLM provider: {provider!r} (expected 'ollama' or 'anthropic')")
