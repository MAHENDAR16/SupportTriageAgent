from __future__ import annotations

from src.graph.deps import GraphDeps
from src.graph.graph_state import GraphState
from src.rules.escalation_rules import detect_escalation_keywords
from src.rules.refund_rules import (
    check_refund_window,
    check_repeat_request,
    detect_refund_abuse_language,
)
from src.rules.required_fields import missing_required_fields


# Factory closing over deps; returns the routing-decision node function.
def make_route_decision_node(deps: GraphDeps):
    # Walks the 10-rule precedence chain (abuse -> refund rules -> escalation
    # -> groundedness -> fabricated citations -> missing fields) to pick a route.
    def route_decision(state: GraphState) -> dict:
        ticket = state["ticket"]
        settings = deps.settings
        category = state.get("detected_category") or ticket.category
        message = ticket.message

        # 1. Abuse -> REFUSE (deterministic, bypasses LLM judgment)
        if state.get("abuse_detected"):
            decision, reason, extra = "REFUSE", "abusive_content_detected", {}

        # 2. Refund-abuse language -> REFUSE. Checked regardless of category
        #    (not gated to refund_request) so it also catches tickets that
        #    were classified/labeled under a different category, e.g. a
        #    refund-abuse message labeled abusive_content.
        elif detect_refund_abuse_language(message, settings):
            decision, reason, extra = "REFUSE", "refund_abuse_language_detected", {}

        # 3. Repeat refund request within the repeat-request window -> ESCALATE
        elif category == "refund_request" and check_repeat_request(ticket, settings):
            decision, reason, extra = "ESCALATE", "repeat_refund_request_within_window", {}

        # 4. Refund outside the refund window -> ESCALATE
        elif category == "refund_request" and not check_refund_window(ticket, settings):
            decision, reason, extra = "ESCALATE", "refund_outside_window", {}

        # 5. KB-mandated escalation (disputes, compromised accounts, ...)
        elif detect_escalation_keywords(category, message, settings):
            decision, reason, extra = "ESCALATE", "policy_mandated_escalation_keywords", {}

        else:
            retrieved_chunks = state.get("retrieved_chunks", [])
            groundedness_score = state.get("groundedness_score", 0.0)

            # 6. No policy found / groundedness below threshold -> ESCALATE.
            #    Checked before the required-fields gate below: if the KB
            #    doesn't cover the topic at all, asking the customer for an
            #    identifier won't make it resolvable, so a missing-policy
            #    signal takes priority over a missing-field signal.
            if not retrieved_chunks:
                decision, reason, extra = "ESCALATE", "no_policy_found", {}
            elif groundedness_score < settings.groundedness_threshold:
                decision, reason, extra = "ESCALATE", "low_groundedness", {}

            # 7. Fabricated citation -> ESCALATE, regardless of score
            elif state.get("fabricated_citations"):
                decision, reason, extra = (
                    "ESCALATE",
                    "fabricated_citation_detected",
                    {"fabricated_citations": state["fabricated_citations"]},
                )

            else:
                missing = missing_required_fields(category, ticket, settings)
                # 8. Missing a required identifier for this category -> ASK_INFO
                if missing:
                    decision, reason, extra = "ASK_INFO", "missing_required_fields", {"missing_fields": missing}

                # 9. Classifier flagged the ticket as needing more info -> ASK_INFO
                elif state.get("requires_more_info"):
                    decision, reason, extra = "ASK_INFO", "classifier_requires_more_info", {}

                # 10. Otherwise, grounded and complete -> AUTO_RESOLVE
                else:
                    decision, reason, extra = "AUTO_RESOLVE", "policy_grounded_response", {}

        output = {"route_decision": decision, "reason": reason, **extra}
        deps.audit_logger.log(ticket.ticket_id, "route_decision", output)

        return {"route_decision": decision, "route_reason": reason}

    return route_decision
