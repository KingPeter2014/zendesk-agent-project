"""Redis-backed shared ticket memory with optimistic locking."""

from __future__ import annotations

import json
import time
from typing import Any

import redis

from memory.models import SharedTicketState, Ticket


class VersionConflictError(Exception):
    """Raised when an optimistic locking conflict is detected."""

    def __init__(self, ticket_id: str, expected: int, actual: int) -> None:
        self.ticket_id = ticket_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict on ticket {ticket_id}: expected {expected}, found {actual}"
        )


class SharedTicketMemory:
    """
    Shared ticket state stored in Redis.
    Uses WATCH/MULTI/EXEC for optimistic locking — raises VersionConflictError
    on stale writes so callers can retry with a fresh read.
    """

    KEY_PREFIX = "ticket:"
    MAX_RETRIES = 5

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        self._redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def _key(self, ticket_id: str) -> str:
        return f"{self.KEY_PREFIX}{ticket_id}"

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, ticket_id: str) -> SharedTicketState | None:
        raw = self._redis.get(self._key(ticket_id))
        if raw is None:
            return None
        return SharedTicketState.model_validate_json(raw)

    def exists(self, ticket_id: str) -> bool:
        return bool(self._redis.exists(self._key(ticket_id)))

    # ------------------------------------------------------------------
    # Write (optimistic locking)
    # ------------------------------------------------------------------

    def create(self, state: SharedTicketState) -> SharedTicketState:
        key = self._key(state.ticket_id)
        if self._redis.exists(key):
            raise ValueError(f"Ticket {state.ticket_id} already exists in shared memory")
        self._redis.set(key, state.model_dump_json())
        return state

    def update(
        self,
        ticket_id: str,
        delta: dict[str, Any],
        expected_version: int,
    ) -> SharedTicketState:
        """
        Atomically apply `delta` fields to the shared state.
        Raises VersionConflictError if another agent has already written a newer version.
        """
        key = self._key(ticket_id)
        pipe = self._redis.pipeline()
        try:
            pipe.watch(key)
            raw = pipe.get(key)
            if raw is None:
                pipe.unwatch()
                raise KeyError(f"Ticket {ticket_id} not found in shared memory")
            state = SharedTicketState.model_validate_json(raw)
            if state.version != expected_version:
                pipe.unwatch()
                raise VersionConflictError(ticket_id, expected_version, state.version)

            updated_data = state.model_dump()
            updated_data.update(delta)
            updated_data["version"] = state.version + 1
            updated_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            new_state = SharedTicketState.model_validate(updated_data)
            pipe.multi()
            pipe.set(key, new_state.model_dump_json())
            pipe.execute()
        finally:
            pipe.reset()

        return new_state

    def update_with_retry(
        self,
        ticket_id: str,
        delta: dict[str, Any],
        max_retries: int = MAX_RETRIES,
    ) -> SharedTicketState:
        """Read-modify-write with automatic retry on version conflict."""
        for attempt in range(max_retries):
            state = self.get(ticket_id)
            if state is None:
                raise KeyError(f"Ticket {ticket_id} not found")
            try:
                return self.update(ticket_id, delta, expected_version=state.version)
            except VersionConflictError:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.05 * (2 ** attempt))
        raise RuntimeError("Should not reach here")

    def delete(self, ticket_id: str) -> None:
        self._redis.delete(self._key(ticket_id))

    # ------------------------------------------------------------------
    # Helpers for initialising from a Ticket
    # ------------------------------------------------------------------

    @classmethod
    def init_from_ticket(
        cls,
        ticket: Ticket,
        host: str = "localhost",
        port: int = 6379,
    ) -> tuple["SharedTicketMemory", SharedTicketState]:
        mem = cls(host=host, port=port)
        state = SharedTicketState(ticket_id=ticket.ticket_id, ticket=ticket)
        if not mem.exists(ticket.ticket_id):
            mem.create(state)
        else:
            state = mem.get(ticket.ticket_id)  # type: ignore[assignment]
        return mem, state
