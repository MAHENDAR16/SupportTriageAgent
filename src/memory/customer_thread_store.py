from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from src.models.ticket import ConversationTurn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customer_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL UNIQUE,
    thread_title TEXT,
    conversation_history TEXT,
    first_message_at TEXT,
    last_message_at TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customer_threads_customer_id ON customer_threads(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_threads_ticket_id ON customer_threads(ticket_id);
CREATE INDEX IF NOT EXISTS idx_customer_threads_created_at ON customer_threads(created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CustomerThreadStore:
    """Persistent storage for customer conversation threads.
    Enables context retrieval across multiple tickets and sessions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_thread(
        self,
        customer_id: str,
        ticket_id: str,
        thread_title: str = "",
        conversation_history: Optional[list[ConversationTurn]] = None,
    ) -> int:
        """Create a new customer conversation thread."""
        history = conversation_history or []
        # Convert Pydantic models to dicts for JSON serialization
        history_dicts = [turn.model_dump() if hasattr(turn, 'model_dump') else turn for turn in history]
        history_json = json.dumps(history_dicts)
        message_count = len(history)

        now = _now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO customer_threads (
                    customer_id, ticket_id, thread_title, conversation_history,
                    message_count, first_message_at, last_message_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_id,
                    ticket_id,
                    thread_title,
                    history_json,
                    message_count,
                    now if history else None,
                    now if history else None,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def get_thread_by_ticket(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a thread by ticket ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customer_threads WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def get_customer_threads(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve all threads for a customer, ordered by most recent."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM customer_threads WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
                (customer_id, limit),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def add_message(self, ticket_id: str, role: str, content: str) -> None:
        """Add a message to an existing thread."""
        thread = self.get_thread_by_ticket(ticket_id)
        if not thread:
            raise ValueError(f"Thread not found for ticket {ticket_id}")

        history = thread["conversation_history"]
        history.append({"role": role, "content": content})

        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE customer_threads
                SET conversation_history = ?, message_count = ?, last_message_at = ?, updated_at = ?
                WHERE ticket_id = ?
                """,
                (json.dumps(history), len(history), now, now, ticket_id),
            )

    def update_thread(
        self,
        ticket_id: str,
        thread_title: Optional[str] = None,
        conversation_history: Optional[list[ConversationTurn]] = None,
    ) -> None:
        """Update thread title and/or conversation history."""
        with self._connect() as conn:
            if thread_title is not None and conversation_history is not None:
                history_dicts = [turn.model_dump() if hasattr(turn, 'model_dump') else turn for turn in conversation_history]
                conn.execute(
                    """
                    UPDATE customer_threads
                    SET thread_title = ?, conversation_history = ?, message_count = ?,
                        last_message_at = ?, updated_at = ?
                    WHERE ticket_id = ?
                    """,
                    (
                        thread_title,
                        json.dumps(history_dicts),
                        len(conversation_history),
                        _now(),
                        _now(),
                        ticket_id,
                    ),
                )
            elif thread_title is not None:
                conn.execute(
                    "UPDATE customer_threads SET thread_title = ?, updated_at = ? WHERE ticket_id = ?",
                    (thread_title, _now(), ticket_id),
                )
            elif conversation_history is not None:
                history_dicts = [turn.model_dump() if hasattr(turn, 'model_dump') else turn for turn in conversation_history]
                conn.execute(
                    """
                    UPDATE customer_threads
                    SET conversation_history = ?, message_count = ?,
                        last_message_at = ?, updated_at = ?
                    WHERE ticket_id = ?
                    """,
                    (
                        json.dumps(history_dicts),
                        len(conversation_history),
                        _now(),
                        _now(),
                        ticket_id,
                    ),
                )

    def delete_thread(self, ticket_id: str) -> None:
        """Delete a conversation thread."""
        with self._connect() as conn:
            conn.execute("DELETE FROM customer_threads WHERE ticket_id = ?", (ticket_id,))

    def get_recent_threads(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get most recent threads across all customers."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM customer_threads ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def search_threads(self, customer_id: str, search_text: str) -> list[dict[str, Any]]:
        """Search threads by thread title for a customer."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM customer_threads WHERE customer_id = ? AND thread_title LIKE ? ORDER BY created_at DESC",
                (customer_id, f"%{search_text}%"),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_customer_conversation_context(self, customer_id: str) -> str:
        """Get formatted conversation context from all recent customer threads."""
        threads = self.get_customer_threads(customer_id, limit=5)
        if not threads:
            return "(no prior conversation history for this customer)"

        context_parts = []
        for thread in threads:
            if thread["thread_title"]:
                context_parts.append(f"Previous topic: {thread['thread_title']}")
            if thread["conversation_history"]:
                for turn in thread["conversation_history"][-3:]:  # Last 3 turns per thread
                    role = turn.get('role') or turn.get('role')
                    content = turn.get('content') or turn.get('content')
                    context_parts.append(f"{role.upper()}: {content}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to a dictionary with parsed JSON."""
        record = dict(row)
        if record.get("conversation_history"):
            record["conversation_history"] = json.loads(record["conversation_history"])
        else:
            record["conversation_history"] = []
        return record

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored threads."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as n FROM customer_threads").fetchone()["n"]
            unique_customers = conn.execute(
                "SELECT COUNT(DISTINCT customer_id) as n FROM customer_threads"
            ).fetchone()["n"]
            total_messages = conn.execute(
                "SELECT SUM(message_count) as n FROM customer_threads"
            ).fetchone()["n"]

        return {
            "total_threads": total,
            "unique_customers": unique_customers,
            "total_messages": total_messages or 0,
            "avg_messages_per_thread": (total_messages or 0) / total if total > 0 else 0,
        }
