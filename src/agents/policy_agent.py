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

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def detect_abuse(self, message: str) -> bool:
        """Check if message contains abusive content."""
        return detect_abuse(message)

    def detect_refund_abuse(self, message: str) -> bool:
        """Check if message contains refund-specific abuse language."""
        return detect_refund_abuse_language(message, self.settings)

    def check_refund_window(self, ticket: Ticket) -> bool:
        """Verify refund request is within the allowed window."""
        return check_refund_window(ticket, self.settings)

    def check_repeat_refund(self, ticket: Ticket) -> bool:
        """Check if this is a repeated refund request within the window."""
        return check_repeat_request(ticket, self.settings)

    def detect_escalation_keywords(self, category: str, message: str) -> bool:
        """Check if message contains policy-mandated escalation keywords."""
        return detect_escalation_keywords(category, message, self.settings)

    def validate_required_fields(self, category: str, ticket: Ticket) -> list[str]:
        """Return list of missing required fields for the ticket category."""
        return missing_required_fields(category, ticket, self.settings)


def build_policy_agent(settings: Settings) -> PolicyAgent:
    """Factory to construct the policy enforcement agent."""
    return PolicyAgent(settings)
