from __future__ import annotations

from dataclasses import dataclass

from src.graph.deps import GraphDeps
from src.graph.graph_state import GraphState


@dataclass
class ReviewTicketDisplay:
    """Formatted review information for display to a human reviewer."""

    ticket_id: str
    route_decision: str
    route_reason: str
    draft_reply: str
    sources: list[str]
    groundedness_score: float
    llm_groundedness_score: float | None = None
    regenerate_count: int = 0


# Pulls the relevant fields out of raw graph state (ticket, route, draft,
# sources, scores) into the typed ReviewTicketDisplay shape.
def format_review_for_display(state: GraphState) -> ReviewTicketDisplay:
    """Convert graph state into a formatted display object for the reviewer UI."""
    ticket = state["ticket"]
    sources = [c["source"] for c in state.get("retrieved_chunks", [])]

    return ReviewTicketDisplay(
        ticket_id=ticket.ticket_id,
        route_decision=state.get("route_decision", "UNKNOWN"),
        route_reason=state.get("route_reason", ""),
        draft_reply=state.get("draft_reply", ""),
        sources=sources,
        groundedness_score=state.get("groundedness_score", 0.0),
        llm_groundedness_score=state.get("llm_groundedness_score"),
        regenerate_count=state.get("regenerate_count", 0),
    )


# Prints ticket id, route, sources, scores, and draft text to stdout.
# Used only in the interactive CLI reviewer path, not the async queue/UI path.
def display_review_cli(display: ReviewTicketDisplay) -> None:
    """Print a formatted review to the terminal for interactive approval."""
    print(f"\n--- Reviewer queue: {display.ticket_id} ---")
    print(f"Route: {display.route_decision} ({display.route_reason})")
    print(f"Sources: {display.sources}")
    print(f"Groundedness: {display.groundedness_score:.4f}")
    if display.llm_groundedness_score is not None:
        print(f"LLM Groundedness: {display.llm_groundedness_score:.4f}")
    if display.regenerate_count > 0:
        print(f"Regeneration: {display.regenerate_count}")
    print(f"Draft:\n{display.draft_reply}")


# Blocks on terminal input for an A/R/E keystroke and optional comment text.
# Defaults to APPROVED if the reviewer enters anything else or presses Enter.
def get_reviewer_action_cli() -> tuple[str, str | None]:
    """Prompt the reviewer for an action via terminal input.
    Returns (action, comments)."""
    action = input("Action [A]pprove / [R]eject / [E]scalate (default Approve): ").strip().upper()
    reviewer_action = {"R": "REJECTED", "E": "ESCALATED"}.get(action, "APPROVED")
    comments = input("Comments (optional): ").strip() or None
    return reviewer_action, comments


class ApprovalUIStub:
    """Interface stub for both CLI and future UI implementations.
    Abstracts the reviewer interaction layer from the graph engine."""

    # Stores deps and the interactive/async mode flag for present_review().
    def __init__(self, deps: GraphDeps, interactive: bool = True):
        self.deps = deps
        self.interactive = interactive

    # In interactive mode, formats and prints the review then blocks for
    # reviewer input; in async mode, returns (None, None) immediately.
    def present_review(self, state: GraphState) -> tuple[str, str | None]:
        """Display a review to the reviewer and collect their action.
        Returns (action, comments_optional).
        If not interactive, returns (None, None) -- action pending."""
        display = format_review_for_display(state)

        if self.interactive:
            display_review_cli(display)
            return get_reviewer_action_cli()

        return None, None
