from __future__ import annotations

from src.config.settings import Settings
from src.models.ticket import Ticket


# Checks the ticket's required identifier fields for this category (per
# app_config.yaml) and returns which ones are still empty/unset.
def missing_required_fields(category: str, ticket: Ticket, settings: Settings) -> list[str]:
    """Only defined for categories listed in app_config.yaml's required_fields
    map. Other categories fall through to the classifier's requires_more_info
    flag instead."""
    field_names = settings.required_fields.get(category, [])
    missing = []
    for field_name in field_names:
        if getattr(ticket, field_name, None) in (None, ""):
            missing.append(field_name)
    return missing
