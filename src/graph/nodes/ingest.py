from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.state import GraphState


def make_ingest_node(deps: GraphDeps):
    def ingest(state: GraphState) -> dict:
        ticket = state["ticket"]

        # Load conversation history into memory
        if ticket.conversation_history:
            deps.conversation_memory.update_from_ticket(
                ticket.ticket_id, ticket.customer_id, ticket.conversation_history
            )

        # Store or update in persistent thread store
        existing_thread = deps.thread_store.get_thread_by_ticket(ticket.ticket_id)
        if existing_thread:
            deps.thread_store.update_thread(
                ticket.ticket_id,
                conversation_history=ticket.conversation_history,
            )
        else:
            deps.thread_store.create_thread(
                ticket.customer_id,
                ticket.ticket_id,
                thread_title=ticket.subject,
                conversation_history=ticket.conversation_history,
            )

        # Get conversation context for LLM usage
        conversation_context = deps.conversation_memory.get_conversation_string(ticket.ticket_id)

        output = {
            "ticket_id": ticket.ticket_id,
            "category_hint": ticket.category,
            "conversation_turns": len(ticket.conversation_history),
        }
        deps.audit_logger.log(ticket.ticket_id, "ingest", output)
        return {
            "retrieval_attempts": 0,
            "conversation_context": conversation_context,
        }

    return ingest
