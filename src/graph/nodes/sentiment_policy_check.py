from __future__ import annotations

from src.agents.sentiment_agent import classify_ticket
from src.graph.deps import GraphDeps
from src.graph.state import GraphState
from src.rules.abuse_detection import detect_abuse


def make_sentiment_policy_check_node(deps: GraphDeps):
    def sentiment_policy_check(state: GraphState) -> dict:
        ticket = state["ticket"]

        abuse_detected = detect_abuse(ticket.message)
        classification = classify_ticket(ticket, deps.llm, deps.settings)

        output = {
            "abuse_detected": abuse_detected,
            "sentiment": classification.sentiment,
            "detected_category": classification.category,
            "requires_more_info": classification.requires_more_info,
            "missing_fields": classification.missing_fields,
        }
        deps.audit_logger.log(ticket.ticket_id, "sentiment_policy_check", output)

        return {
            "abuse_detected": abuse_detected,
            "sentiment": classification.sentiment,
            "detected_category": classification.category,
            "requires_more_info": classification.requires_more_info,
            "missing_fields": classification.missing_fields,
        }

    return sentiment_policy_check
