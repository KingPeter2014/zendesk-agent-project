"""LLM-as-judge: rates whether a support response adequately resolves a ticket.

Uses the same local Ollama model as the rest of this project
(see `agents/meta_planner.py`). Requires Ollama running with
`mistral:7b-instruct` pulled -- `docker-compose up -d` from the project
root if it isn't already.
"""

from __future__ import annotations

from langchain_ollama import OllamaLLM

JUDGE_PROMPT = """You are reviewing a customer support response for quality.

Ticket: {ticket_body}

Response: {response}

Does this response adequately resolve the customer's request? Reply with
exactly one word: PASS or FAIL."""


class LLMJudge:
    def __init__(
        self,
        model: str = "mistral:7b-instruct",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
    ) -> None:
        self._llm = OllamaLLM(model=model, base_url=base_url, temperature=temperature)

    def judge(self, ticket_body: str, response: str) -> str:
        prompt = JUDGE_PROMPT.format(ticket_body=ticket_body, response=response)
        result = self._llm.generate([prompt])
        text = result.generations[0][0].text.strip().upper()
        return "PASS" if "PASS" in text else "FAIL"
