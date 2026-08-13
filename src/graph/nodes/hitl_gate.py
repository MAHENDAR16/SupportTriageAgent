from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.state import GraphState


def make_hitl_gate_node(deps: GraphDeps):
    def hitl_gate(state: GraphState) -> dict:
        ticket = state["ticket"]
        sources = [c["source"] for c in state.get("retrieved_chunks", [])]

        if deps.auto_approve:
            reviewer_action = "APPROVED"
            reviewer_comments = "auto-approved (batch/eval run, no human reviewer in the loop)"
            status = "APPROVED"
        elif deps.interactive:
            print(f"\n--- Reviewer queue: {ticket.ticket_id} ---")
            print(f"Route: {state.get('route_decision')} ({state.get('route_reason')})")
            print(f"Sources: {sources}")
            print(f"Groundedness: {state.get('groundedness_score')}")
            print(f"Draft:\n{state.get('draft_reply')}")
            action = input("Action [A]pprove / [R]eject / [E]scalate (default Approve): ").strip().upper()
            reviewer_action = {"R": "REJECTED", "E": "ESCALATED"}.get(action, "APPROVED")
            reviewer_comments = input("Comments (optional): ").strip() or None
            status = reviewer_action
        else:
            # Async queue mode (e.g. the Streamlit UI reviews later) -- do
            # not block; leave the ticket pending for a human action.
            reviewer_action = None
            reviewer_comments = None
            status = "PENDING_REVIEW"

        review_id = None
        if deps.review_store is not None:
            review_id = deps.review_store.insert_review(
                ticket_id=ticket.ticket_id,
                customer_id=ticket.customer_id,
                subject=ticket.subject,
                message=ticket.message,
                draft_reply=state.get("draft_reply", ""),
                route_decision=state.get("route_decision", ""),
                route_reason=state.get("route_reason", ""),
                confidence_score=state.get("groundedness_score"),
                llm_groundedness_score=state.get("llm_groundedness_score"),
                retrieved_sources=sources,
                reviewer_action=reviewer_action,
                status=status,
                regenerate_count=deps.review_store.count_for_ticket(ticket.ticket_id),
            )

        output = {"reviewer_action": reviewer_action, "reviewer_comments": reviewer_comments, "review_id": review_id}
        deps.audit_logger.log(
            ticket.ticket_id,
            "hitl_gate",
            {k: v for k, v in output.items()},
            actor="system" if deps.auto_approve else ("reviewer:cli" if deps.interactive else "system"),
        )

        return output

    return hitl_gate
