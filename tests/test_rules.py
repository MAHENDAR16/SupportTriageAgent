from src.config.settings import get_settings
from src.models.ticket import Ticket
from src.rules.abuse_detection import detect_abuse
from src.rules.escalation_rules import detect_escalation_keywords
from src.rules.refund_rules import (
    check_refund_window,
    check_repeat_request,
    detect_refund_abuse_language,
)
from src.rules.required_fields import missing_required_fields

settings = get_settings()


def _ticket(**overrides) -> Ticket:
    base = dict(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="test",
        message="test message",
        category="refund_request",
    )
    base.update(overrides)
    return Ticket(**base)


def test_refund_window_within():
    ticket = _ticket(days_since_purchase=7)
    assert check_refund_window(ticket, settings) is True


def test_refund_window_outside():
    ticket = _ticket(days_since_purchase=8)
    assert check_refund_window(ticket, settings) is False


def test_refund_window_unknown_purchase_date():
    ticket = _ticket(days_since_purchase=None)
    assert check_refund_window(ticket, settings) is False


def test_repeat_request_detected():
    ticket = _ticket(previous_refund_request_count=1, days_since_last_refund_request=30)
    assert check_repeat_request(ticket, settings) is True


def test_repeat_request_outside_window_not_flagged():
    ticket = _ticket(previous_refund_request_count=1, days_since_last_refund_request=120)
    assert check_repeat_request(ticket, settings) is False


def test_repeat_request_no_prior_requests():
    ticket = _ticket(previous_refund_request_count=0, days_since_last_refund_request=None)
    assert check_repeat_request(ticket, settings) is False


def test_refund_abuse_language_detected():
    assert detect_refund_abuse_language(
        "I already used it every day and will keep asking", settings
    ) is True


def test_refund_abuse_language_absent():
    assert detect_refund_abuse_language("Please refund my order", settings) is False


def test_abuse_detection_hostile_message():
    assert detect_abuse("You people are useless and incompetent idiots") is True


def test_abuse_detection_neutral_message():
    assert detect_abuse("I was billed twice this month and want this investigated.") is False


def test_escalation_keywords_dispute():
    assert detect_escalation_keywords(
        "subscription_cancellation", "I want to dispute this charge", settings
    ) is True


def test_escalation_keywords_no_match():
    assert detect_escalation_keywords(
        "subscription_cancellation", "please cancel my plan", settings
    ) is False


def test_missing_required_fields_present():
    ticket = _ticket(category="refund_request", order_id=None)
    assert missing_required_fields("refund_request", ticket, settings) == ["order_id"]


def test_missing_required_fields_satisfied():
    ticket = _ticket(category="refund_request", order_id="ORD-1")
    assert missing_required_fields("refund_request", ticket, settings) == []


def test_missing_required_fields_category_not_configured():
    ticket = _ticket(category="troubleshooting")
    assert missing_required_fields("troubleshooting", ticket, settings) == []
