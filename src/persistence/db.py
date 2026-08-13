from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    customer_id TEXT,
    subject TEXT,
    message TEXT,
    draft_reply TEXT,
    route_decision TEXT,
    route_reason TEXT,
    confidence_score REAL,
    llm_groundedness_score REAL,
    retrieved_sources TEXT,
    reviewer_action TEXT,
    reviewer_comments TEXT,
    edited_reply TEXT,
    status TEXT NOT NULL,
    regenerate_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_ticket_id ON reviews(ticket_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewStore:
    """Persists the reviewer queue: one row per graph run (including
    regenerations), so reviewer-action history accumulates over time instead
    of being overwritten. Uses a fresh connection per call -- sqlite3
    connections aren't safe to share across threads, and Streamlit may call
    in from a different thread than the one that constructed this object."""

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

    def insert_review(
        self,
        *,
        ticket_id: str,
        customer_id: str,
        subject: str,
        message: str,
        draft_reply: str,
        route_decision: str,
        route_reason: str,
        confidence_score: Optional[float],
        llm_groundedness_score: Optional[float],
        retrieved_sources: list[str],
        reviewer_action: Optional[str],
        status: str,
        regenerate_count: int = 0,
    ) -> int:
        now = _now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reviews (
                    ticket_id, customer_id, subject, message, draft_reply,
                    route_decision, route_reason, confidence_score,
                    llm_groundedness_score, retrieved_sources, reviewer_action,
                    status, regenerate_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    customer_id,
                    subject,
                    message,
                    draft_reply,
                    route_decision,
                    route_reason,
                    confidence_score,
                    llm_groundedness_score,
                    json.dumps(retrieved_sources),
                    reviewer_action,
                    status,
                    regenerate_count,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_review(
        self,
        review_id: int,
        *,
        reviewer_action: str,
        status: str,
        reviewer_comments: Optional[str] = None,
        edited_reply: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reviews
                SET reviewer_action = ?, status = ?, reviewer_comments = ?,
                    edited_reply = ?, updated_at = ?
                WHERE id = ?
                """,
                (reviewer_action, status, reviewer_comments, edited_reply, _now(), review_id),
            )

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        record = dict(row)
        record["retrieved_sources"] = json.loads(record["retrieved_sources"] or "[]")
        return record

    def list_pending(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE status = 'PENDING_REVIEW' ORDER BY created_at ASC"
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def list_all(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get(self, review_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def count_for_ticket(self, ticket_id: str) -> int:
        """Number of review rows already recorded for this ticket -- used as
        the new row's regenerate_count (0 for the first run, 1 for the first
        regeneration, ...)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM reviews WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
            return int(row["n"])
