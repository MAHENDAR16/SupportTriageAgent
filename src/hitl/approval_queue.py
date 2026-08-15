from __future__ import annotations

from src.config.settings import Settings
from src.graph.deps import GraphDeps
from src.main import load_tickets


# Reads the full ticket dataset and builds a ticket_id -> Ticket lookup dict.
# Used by the Streamlit UI to resolve pending review rows back to full tickets.
def load_tickets_by_id(settings: Settings) -> dict:
    """Load all tickets indexed by ticket_id for quick lookup."""
    return {t.ticket_id: t for t in load_tickets(settings)}


# Delegates to the ReviewStore to fetch rows still awaiting a reviewer action.
def list_pending(deps: GraphDeps) -> list[dict]:
    """Retrieve all reviews pending human approval, oldest first."""
    return deps.review_store.list_pending()


# Delegates to the ReviewStore to fetch the full review history.
def list_all(deps: GraphDeps) -> list[dict]:
    """Retrieve all reviews ever created, newest first."""
    return deps.review_store.list_all()


# Delegates to the ReviewStore to look up one review row by its id.
def get_review(review_id: int, deps: GraphDeps) -> dict | None:
    """Retrieve a single review record by id."""
    return deps.review_store.get(review_id)


# Counts pending reviews by calling list_pending() and taking its length.
def count_pending(deps: GraphDeps) -> int:
    """Count the number of reviews awaiting approval."""
    pending = list_pending(deps)
    return len(pending)
