from __future__ import annotations

from src.agents.policy_agent import PolicyAgent
from src.agents.rag_agent import RAGAgent
from src.agents.response_agent import compute_groundedness, find_fabricated_citations
from src.agents.sentiment_agent import ClassificationResult
from src.config.settings import Settings
from src.graph.state import RetrievedChunk
from src.models.ticket import Ticket


class TriageAgent:
    """Main triage orchestrator: evaluates support tickets through a decision pipeline,
    combining sentiment analysis, policy enforcement, retrieval-augmented generation,
    and confidence scoring to route tickets (AUTO_RESOLVE, ESCALATE, REFUSE, ASK_INFO)."""

    def __init__(
        self,
        settings: Settings,
        rag_agent: RAGAgent,
        policy_agent: PolicyAgent,
    ) -> None:
        self.settings = settings
        self.rag_agent = rag_agent
        self.policy_agent = policy_agent

    def make_routing_decision(
        self,
        ticket: Ticket,
        classification: ClassificationResult,
        abuse_detected: bool,
        retrieved_chunks: list[RetrievedChunk],
        draft_reply: str,
        fabricated_citations: list[str],
    ) -> tuple[str, str]:
        """
        Evaluate conditions in precedence order to determine ticket route and reason.
        Returns (route_decision, route_reason).
        """
        # 1. Abuse detected
        if abuse_detected:
            return "REFUSE", "abusive_content_detected"

        # 2. Refund abuse language
        if self.policy_agent.detect_refund_abuse(ticket.message):
            return "REFUSE", "refund_abuse_language_detected"

        # 3. Repeat refund request
        if ticket.category == "refund_request" and self.policy_agent.check_repeat_refund(ticket):
            return "ESCALATE", "repeat_refund_request_within_window"

        # 4. Refund outside window
        if ticket.category == "refund_request" and not self.policy_agent.check_refund_window(ticket):
            return "ESCALATE", "refund_outside_window"

        # 5. Escalation keywords
        category = classification.category or ticket.category
        if self.policy_agent.detect_escalation_keywords(category, ticket.message):
            return "ESCALATE", "policy_mandated_escalation_keywords"

        # 6. No retrieved chunks or low groundedness
        if not retrieved_chunks:
            return "ESCALATE", "no_policy_found"
        groundedness_score = compute_groundedness(retrieved_chunks)
        if groundedness_score < self.settings.groundedness_threshold:
            return "ESCALATE", "low_groundedness"

        # 7. Fabricated citations
        if fabricated_citations:
            return "ESCALATE", "fabricated_citation_detected"

        # 8. Missing required fields
        missing_fields = self.policy_agent.validate_required_fields(category, ticket)
        if missing_fields:
            return "ASK_INFO", "missing_required_fields"

        # 9. Classifier requires more info
        if classification.requires_more_info:
            return "ASK_INFO", "classifier_requires_more_info"

        # 10. Default: auto-resolve
        return "AUTO_RESOLVE", "policy_grounded_response"


def build_triage_agent(
    settings: Settings,
    rag_agent: RAGAgent,
    policy_agent: PolicyAgent,
) -> TriageAgent:
    """Factory to construct the main triage agent."""
    return TriageAgent(settings, rag_agent, policy_agent)
