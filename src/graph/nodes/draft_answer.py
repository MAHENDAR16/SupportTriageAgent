from __future__ import annotations

from src.agents.response_agent import compute_groundedness, draft_answer as generate_draft, find_fabricated_citations
from src.graph.deps import GraphDeps
from src.graph.state import GraphState
from src.rules.refund_rules import detect_refund_abuse_language


def make_draft_answer_node(deps: GraphDeps):
    def draft_answer(state: GraphState) -> dict:
        ticket = state["ticket"]
        retrieved_chunks = state.get("retrieved_chunks", [])
        groundedness_score = compute_groundedness(retrieved_chunks)

        # Refusal path is scripted, not generative -- avoids tone drift or
        # leaking internal reasoning, and never calls the LLM at all.
        if state.get("abuse_detected"):
            draft_reply = deps.settings.refusal_templates["abusive"]
            fabricated: list[str] = []
        elif detect_refund_abuse_language(ticket.message, deps.settings):
            draft_reply = deps.settings.refusal_templates["refund_abuse"]
            fabricated = []
        else:
            draft_reply = generate_draft(ticket, retrieved_chunks, deps.llm)
            fabricated = find_fabricated_citations(draft_reply, retrieved_chunks)

        output = {
            "draft_reply": draft_reply,
            "groundedness_score": round(groundedness_score, 4),
            "fabricated_citations": fabricated,
        }
        deps.audit_logger.log(ticket.ticket_id, "draft_answer", output)

        return {
            "draft_reply": draft_reply,
            "groundedness_score": groundedness_score,
            "fabricated_citations": fabricated,
        }

    return draft_answer
