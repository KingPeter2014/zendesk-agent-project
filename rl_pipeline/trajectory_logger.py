"""Logs agent trajectories to SQLite for offline RL training."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.metrics import compute_cost_usd
from memory.models import Trajectory
from memory.sqlite_store import SqliteStore


class TrajectoryLogger(SqliteStore):

    def __init__(self, db_path: str | Path = "data/trajectories.db") -> None:
        super().__init__(db_path)

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trajectories (
                trajectory_id TEXT PRIMARY KEY,
                ticket_id     TEXT NOT NULL,
                agent_id      TEXT NOT NULL,
                steps_json    TEXT NOT NULL,
                outcome       TEXT,
                reward        REAL,
                latency_ms    REAL,
                input_tokens  INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

    def log(self, trajectory: Trajectory) -> None:
        steps_json = json.dumps(
            [s.model_dump(mode="json") for s in trajectory.steps], default=str
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO trajectories
                (trajectory_id, ticket_id, agent_id, steps_json, outcome, reward, latency_ms,
                 input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trajectory.trajectory_id,
                trajectory.ticket_id,
                trajectory.agent_id,
                steps_json,
                trajectory.outcome.value if trajectory.outcome else None,
                trajectory.reward,
                trajectory.total_latency_ms,
                trajectory.input_tokens,
                trajectory.output_tokens,
            ),
        )
        self._conn.commit()

    def fetch_all(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT trajectory_id, ticket_id, agent_id, steps_json, outcome, reward, latency_ms, "
            "input_tokens, output_tokens, created_at "
            "FROM trajectories ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "trajectory_id": r[0],
                "ticket_id": r[1],
                "agent_id": r[2],
                "steps": json.loads(r[3]),
                "outcome": r[4],
                "reward": r[5],
                "latency_ms": r[6],
                "input_tokens": r[7],
                "output_tokens": r[8],
                "total_tokens": r[7] + r[8],
                "cost_usd": compute_cost_usd(r[7], r[8]),
                "created_at": r[9],
            }
            for r in rows
        ]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM trajectories").fetchone()[0]
