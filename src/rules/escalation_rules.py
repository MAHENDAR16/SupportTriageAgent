from __future__ import annotations

from src.config.settings import Settings


def detect_escalation_keywords(category: str, message: str, settings: Settings) -> bool:
    """Turns KB "escalate on X" guidance (renewal disputes, compromised
    accounts, etc.) into a checkable rule instead of leaving it implicit in
    retrieved text."""
    keywords = settings.escalation_keywords.get(category, [])
    lowered = message.lower()
    return any(keyword.lower() in lowered for keyword in keywords)
