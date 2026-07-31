"""Base class for small SQLite-backed stores (per-agent memory, trajectory logs, etc.)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteStore:
    """Opens a SQLite connection at `db_path` and runs the subclass's schema DDL."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        """Override to CREATE TABLE IF NOT EXISTS ... and commit."""
        raise NotImplementedError

    def close(self) -> None:
        self._conn.close()
