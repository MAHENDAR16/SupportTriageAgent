from __future__ import annotations

from src.config.settings import Settings
from src.models.ticket import Ticket
from src.rules.abuse_detection import detect_abuse
from src.rules.escalation_rules import detect_escalation_keywords
from src.rules.refund_rules import check_refund_window, check_repeat_request, detect_refund_abuse_language
from src.rules.required_fields import missing_required_fields


class PolicyAgent:
    """Enforces support policies through deterministic rules: abuse detection,
    refund policies, escalation criteria, and required field validation."""

    # Stores the Settings instance so every delegated rule check below has
    # access to configured thresholds/windows/keyword lists.
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # Delegates to the deterministic keyword-based abuse check.
    # Returns True if the message contains hostile/abusive language.
    def detect_abuse(self, message: str) -> bool:
        """Check if message contains abusive content."""
        return detect_abuse(message)

    # Delegates to the refund-specific abuse-language rule.
    # Returns True if the message matches refund-abuse phrasing.
    def detect_refund_abuse(self, message: str) -> bool:
        """Check if message contains refund-specific abuse language."""
        return detect_refund_abuse_language(message, self.settings)

    # Delegates to the refund-window rule using configured settings.
    # Returns True if the ticket's purchase is still within the refund window.
    def check_refund_window(self, ticket: Ticket) -> bool:
        """Verify refund request is within the allowed window."""
        return check_refund_window(ticket, self.settings)

    # Delegates to the repeat-refund-request rule.
    # Returns True if this customer has requested a refund again within the window.
    def check_repeat_refund(self, ticket: Ticket) -> bool:
        """Check if this is a repeated refund request within the window."""
        return check_repeat_request(ticket, self.settings)

    # Delegates to the escalation-keyword rule for the given category.
    # Returns True if the message contains a policy-mandated escalation term.
    def detect_escalation_keywords(self, category: str, message: str) -> bool:
        """Check if message contains policy-mandated escalation keywords."""
        return detect_escalation_keywords(category, message, self.settings)

    # Delegates to the required-fields rule for the ticket's category.
    # Returns the list of identifier fields still missing from the ticket.
    def validate_required_fields(self, category: str, ticket: Ticket) -> list[str]:
        """Return list of missing required fields for the ticket category."""
        return missing_required_fields(category, ticket, self.settings)


# Factory that wraps Settings into a PolicyAgent instance.
# Used wherever the policy-enforcement agent needs to be constructed.
def build_policy_agent(settings: Settings) -> PolicyAgent:
    """Factory to construct the policy enforcement agent."""
    return PolicyAgent(settings)
