from __future__ import annotations

from src.agents.response_agent import judge_groundedness
from src.graph.deps import GraphDeps
from src.graph.graph_state import GraphState


# Factory closing over deps; returns the confidence-recheck node function.
def make_confidence_recheck_node(deps: GraphDeps):
    """Only reached when route_decision == AUTO_RESOLVE (see build_graph's
    conditional edges). Runs a stricter LLM-as-judge check on the actual
    drafted text -- catching claims that drift from the retrieved context
    even when the coarse retrieval-similarity gate in route_decision passed.
    Retries retrieval with a reformulated query up to max_retrieval_attempts
    before forcing ESCALATE."""

    # Judges groundedness of the draft; on failure either signals a retry
    # (if attempts remain) or force-overrides route_decision to ESCALATE.
    def confidence_recheck(state: GraphState) -> dict:
        ticket = state["ticket"]
        settings = deps.settings
        judgment = judge_groundedness(
            state.get("draft_reply", ""), state.get("retrieved_chunks", []), deps.llm
        )
        passed = judgment.score >= settings.llm_groundedness_threshold and not judgment.unsupported_claims
        attempts = state.get("retrieval_attempts", 0)

        base_output = {
            "llm_groundedness_score": judgment.score,
            "unsupported_claims": judgment.unsupported_claims,
            "retrieval_attempts": attempts,
        }

        if passed:
            deps.audit_logger.log(ticket.ticket_id, "confidence_recheck", {**base_output, "action": "proceed"})
            return {
                "llm_groundedness_score": judgment.score,
                "unsupported_claims": judgment.unsupported_claims,
                "llm_groundedness_passed": True,
                "query_reformulation_hint": "",
            }

        if attempts < settings.max_retrieval_attempts:
            hint = " ".join(judgment.unsupported_claims) or ticket.message
            deps.audit_logger.log(
                ticket.ticket_id, "confidence_recheck", {**base_output, "action": "retry", "query_hint": hint}
            )
            return {
                "llm_groundedness_score": judgment.score,
                "unsupported_claims": judgment.unsupported_claims,
                "llm_groundedness_passed": False,
                "query_reformulation_hint": hint,
            }

        deps.audit_logger.log(ticket.ticket_id, "confidence_recheck", {**base_output, "action": "force_escalate"})
        return {
            "llm_groundedness_score": judgment.score,
            "unsupported_claims": judgment.unsupported_claims,
            "llm_groundedness_passed": False,
            "query_reformulation_hint": "",
            "route_decision": "ESCALATE",
            "route_reason": "low_confidence_after_retries",
        }

    return confidence_recheck
