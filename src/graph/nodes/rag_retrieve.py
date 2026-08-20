from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.graph_state import GraphState


# Factory closing over deps; returns the KB retrieval node function.
def make_rag_retrieve_node(deps: GraphDeps):
    # Runs similarity search against the knowledge base, widening the query
    # with a reformulation hint and larger k on confidence_recheck retries.
    def rag_retrieve(state: GraphState) -> dict:
        ticket = state["ticket"]
        base_query = f"{ticket.subject} {ticket.message}"

        # On a confidence_recheck retry, reformulate the query with the
        # specific claims the LLM judge flagged as unsupported, and widen k,
        # to try to surface additional grounding context instead of just
        # repeating the same search.
        hint = state.get("query_reformulation_hint")
        query = f"{base_query} {hint}" if hint else base_query
        k = 5 if hint else 3

        chunks = deps.retriever.retrieve(query, k=k)

        output = {
            "retrieved_sources": [c["source"] for c in chunks],
            "scores": [round(c["score"], 3) for c in chunks],
            "reformulated": bool(hint),
        }
        deps.audit_logger.log(ticket.ticket_id, "rag_retrieve", output)

        return {
            "retrieved_chunks": chunks,
            "retrieval_attempts": state.get("retrieval_attempts", 0) + 1,
        }

    return rag_retrieve
