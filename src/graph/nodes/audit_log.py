from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.state import GraphState


def make_audit_log_node(deps: GraphDeps):
    """Final rollup entry summarizing the terminal decision, in addition to
    the per-node entries each earlier node already logs."""

    def audit_log(state: GraphState) -> dict:
        ticket = state["ticket"]
        output = {
            "route_decision": state.get("route_decision"),
            "route_reason": state.get("route_reason"),
            "retrieved_sources": [c["source"] for c in state.get("retrieved_chunks", [])],
            "groundedness_score": state.get("groundedness_score"),
            "reviewer_action": state.get("reviewer_action"),
        }
        deps.audit_logger.log(ticket.ticket_id, "audit_log", output)
        return {}

    return audit_log
