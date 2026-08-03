"""Shared helpers for the Streamlit UI — bootstraps the agent system once per session."""

from __future__ import annotations

import sys
import os

# Ensure project root is on the path when running from ui/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st


@st.cache_resource(show_spinner="Initialising agent system…")
def get_system():
    """Bootstrap all agents, memory, and guardrails — cached for the session."""
    from memory.shared_memory import SharedTicketMemory
    from agents.system_bootstrap import build_full_system

    try:
        shared_memory = SharedTicketMemory()
        # Quick connection test
        shared_memory._redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
        shared_memory = None

    system = build_full_system(shared_memory)
    system["redis_ok"] = redis_ok
    system["ollama_ok"] = _check_ollama()
    return system


def _check_ollama() -> bool:
    import os
    import requests

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def status_badge(ok: bool, label: str) -> str:
    return f"🟢 {label}" if ok else f"🔴 {label}"
