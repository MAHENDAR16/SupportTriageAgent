from __future__ import annotations

from src.config.settings import Settings
from src.models.ticket import Ticket


# Compares the ticket's days_since_purchase against the configured refund
# window (from routing_rules.yaml).
def check_refund_window(ticket: Ticket, settings: Settings) -> bool:
    """True if the refund request is within the configured window.
    A ticket with no known purchase date cannot be confirmed in-window."""
    window_days = settings.refund_rules["refund_window_days"]
    if ticket.days_since_purchase is None:
        return False
    return ticket.days_since_purchase <= window_days


# Checks whether this customer's last refund request falls within the
# configured repeat-request window, flagging a possible repeat abuse case.
def check_repeat_request(ticket: Ticket, settings: Settings) -> bool:
    repeat_window_days = settings.refund_rules["repeated_request_window_days"]
    if ticket.previous_refund_request_count <= 0:
        return False
    if ticket.days_since_last_refund_request is None:
        return False
    return ticket.days_since_last_refund_request <= repeat_window_days


# Deterministic keyword scan for refund-abuse phrasing (e.g. persistent
# demands despite having used the service), separate from general abuse detection.
def detect_refund_abuse_language(message: str, settings: Settings) -> bool:
    keywords = settings.refund_rules.get("abuse_language_keywords", [])
    lowered = message.lower()
    return any(keyword.lower() in lowered for keyword in keywords)
