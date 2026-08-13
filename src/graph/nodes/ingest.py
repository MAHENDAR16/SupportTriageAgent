from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.state import GraphState


def make_ingest_node(deps: GraphDeps):
    def ingest(state: GraphState) -> dict:
        ticket = state["ticket"]
        output = {"ticket_id": ticket.ticket_id, "category_hint": ticket.category}
        deps.audit_logger.log(ticket.ticket_id, "ingest", output)
        return {"retrieval_attempts": 0}

    return ingest
