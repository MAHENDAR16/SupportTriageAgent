from __future__ import annotations

from src.graph.deps import GraphDeps

VALID_ACTIONS = {"APPROVED", "REJECTED", "EDITED", "ESCALATED"}


# Looks up the Ticket object by id and invokes the compiled graph on it.
# Called by the Streamlit UI's "Run agent" action for a specific ticket.
def process_ticket(ticket_id: str, deps: GraphDeps, graph, tickets_by_id: dict) -> dict:
    """Runs the full graph for a ticket, leaving a PENDING_REVIEW row in the
    database rather than blocking for input (queue/async mode)."""
    ticket = tickets_by_id[ticket_id]
    return graph.invoke({"ticket": ticket})


# Supersedes the prior review row, then re-invokes process_ticket() so a
# fresh draft is generated and queued for review.
def regenerate(review_id: int, deps: GraphDeps, graph, tickets_by_id: dict) -> dict:
    """Marks the existing review as SUPERSEDED and re-runs the graph for the
    same ticket, producing a fresh draft as a new pending row."""
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


# Validates the action against VALID_ACTIONS, then writes it plus comments
# (and edited_reply, only for EDITED) to the review row via the ReviewStore.
def submit_review(
    review_id: int,
    action: str,
    deps: GraphDeps,
    comments: str | None = None,
    edited_reply: str | None = None,
) -> None:
    """Record a reviewer's decision (approve/reject/edit/escalate) on a pending
    review, updating both reviewer_action and status in the database."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported review action: {action}. Expected one of {sorted(VALID_ACTIONS)}")
    deps.review_store.update_review(
        review_id,
        reviewer_action=action,
        status=action,
        reviewer_comments=comments,
        edited_reply=edited_reply if action == "EDITED" else None,
    )


# Thin wrapper: submits an APPROVED decision for the given review.
def approve_review(review_id: int, deps: GraphDeps, comments: str | None = None) -> None:
    """Approve a review."""
    submit_review(review_id, "APPROVED", deps, comments=comments)


# Thin wrapper: submits a REJECTED decision for the given review.
def reject_review(review_id: int, deps: GraphDeps, comments: str | None = None) -> None:
    """Reject a review."""
    submit_review(review_id, "REJECTED", deps, comments=comments)


# Thin wrapper: submits an EDITED decision, carrying the reviewer's rewritten reply.
def edit_review(review_id: int, edited_reply: str, deps: GraphDeps, comments: str | None = None) -> None:
    """Edit and approve a review with a modified response."""
    submit_review(review_id, "EDITED", deps, comments=comments, edited_reply=edited_reply)


# Thin wrapper: submits an ESCALATED decision for the given review.
def escalate_review(review_id: int, deps: GraphDeps, comments: str | None = None) -> None:
    """Escalate a review for human review outside the system."""
    submit_review(review_id, "ESCALATED", deps, comments=comments)
