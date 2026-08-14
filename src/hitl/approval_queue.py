from __future__ import annotations

from src.config.settings import Settings
from src.graph.deps import GraphDeps
from src.main import load_tickets


def load_tickets_by_id(settings: Settings) -> dict:
    """Load all tickets indexed by ticket_id for quick lookup."""
    return {t.ticket_id: t for t in load_tickets(settings)}


def list_pending(deps: GraphDeps) -> list[dict]:
    """Retrieve all reviews pending human approval, oldest first."""
    return deps.review_store.list_pending()


def list_all(deps: GraphDeps) -> list[dict]:
    """Retrieve all reviews ever created, newest first."""
    return deps.review_store.list_all()


def get_review(review_id: int, deps: GraphDeps) -> dict | None:
    """Retrieve a single review record by id."""
    return deps.review_store.get(review_id)


def count_pending(deps: GraphDeps) -> int:
    """Count the number of reviews awaiting approval."""
    pending = list_pending(deps)
    return len(pending)
