"""SQLite-backed per-agent private memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory.sqlite_store import SqliteStore


class PerAgentMemory(SqliteStore):
    """
    Lightweight key-value store scoped to (agent_id, ticket_id).
    Uses SQLite so it persists across process restarts during a demo run.
    """

    def __init__(self, db_path: str | Path = "data/per_agent_memory.db") -> None:
        super().__init__(db_path)

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                agent_id  TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                updated_at REAL DEFAULT (unixepoch('now')),
                PRIMARY KEY (agent_id, ticket_id, key)
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def set(self, agent_id: str, ticket_id: str, key: str, value: Any) -> None:
        self._conn.execute(
            """
            INSERT INTO agent_memory (agent_id, ticket_id, key, value, updated_at)
            VALUES (?, ?, ?, ?, unixepoch('now'))
            ON CONFLICT(agent_id, ticket_id, key) DO UPDATE
                SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (agent_id, ticket_id, key, json.dumps(value)),
        )
        self._conn.commit()

    def get(self, agent_id: str, ticket_id: str, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM agent_memory WHERE agent_id=? AND ticket_id=? AND key=?",
            (agent_id, ticket_id, key),
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def get_all(self, agent_id: str, ticket_id: str) -> dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM agent_memory WHERE agent_id=? AND ticket_id=?",
            (agent_id, ticket_id),
        ).fetchall()
        return {k: json.loads(v) for k, v in rows}

    def delete(self, agent_id: str, ticket_id: str, key: str) -> None:
        self._conn.execute(
            "DELETE FROM agent_memory WHERE agent_id=? AND ticket_id=? AND key=?",
            (agent_id, ticket_id, key),
        )
        self._conn.commit()

    def clear_ticket(self, agent_id: str, ticket_id: str) -> None:
        self._conn.execute(
            "DELETE FROM agent_memory WHERE agent_id=? AND ticket_id=?",
            (agent_id, ticket_id),
        )
        self._conn.commit()
