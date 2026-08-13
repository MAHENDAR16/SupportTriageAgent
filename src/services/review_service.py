from __future__ import annotations

from src.config.settings import Settings
from src.graph.deps import GraphDeps
from src.main import load_tickets

VALID_ACTIONS = {"APPROVED", "REJECTED", "EDITED", "ESCALATED"}


def load_tickets_by_id(settings: Settings) -> dict:
    return {t.ticket_id: t for t in load_tickets(settings)}


def list_pending(deps: GraphDeps) -> list[dict]:
    return deps.review_store.list_pending()


def list_all(deps: GraphDeps) -> list[dict]:
    return deps.review_store.list_all()


def process_ticket(ticket_id: str, deps: GraphDeps, graph, tickets_by_id: dict) -> dict:
    """Runs the full graph for a ticket in queue mode (deps.interactive and
    deps.auto_approve are both expected to be False), leaving a
    PENDING_REVIEW row in the DB rather than blocking for input."""
    ticket = tickets_by_id[ticket_id]
    return graph.invoke({"ticket": ticket})


def regenerate(review_id: int, deps: GraphDeps, graph, tickets_by_id: dict) -> dict:
    """Marks the existing pending row superseded and re-runs the graph for
    the same ticket, producing a fresh draft as a new pending row."""
    record = deps.review_store.get(review_id)
    if record is None:
        raise ValueError(f"No review found with id {review_id}")
    deps.review_store.update_review(
        review_id,
        reviewer_action="REGENERATED",
        status="SUPERSEDED",
        reviewer_comments="superseded by a reviewer-requested regeneration",
    )
    return process_ticket(record["ticket_id"], deps, graph, tickets_by_id)


def submit_review(
    review_id: int,
    action: str,
    deps: GraphDeps,
    comments: str | None = None,
    edited_reply: str | None = None,
) -> None:
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported review action: {action}. Expected one of {sorted(VALID_ACTIONS)}")
    deps.review_store.update_review(
        review_id,
        reviewer_action=action,
        status=action,
        reviewer_comments=comments,
        edited_reply=edited_reply if action == "EDITED" else None,
    )
