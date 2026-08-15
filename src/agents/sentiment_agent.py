from __future__ import annotations

import json
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from src.config.settings import Settings
from src.models.ticket import Ticket

CATEGORIES = Literal[
    "refund_request",
    "subscription_cancellation",
    "login_access",
    "troubleshooting",
    "abusive_content",
    "other",
]


class ClassificationResult(BaseModel):
    sentiment: Literal["positive", "neutral", "negative", "abusive"]
    category: CATEGORIES
    requires_more_info: bool
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("requires_more_info", mode="before")
    @classmethod
    def _coerce_bool(cls, value):
        # Groq's structured/tool-call output occasionally returns a string
        # ("true"/"false") instead of a JSON boolean; tolerate it here
        # rather than crashing the whole ticket run on a malformed response.
        if isinstance(value, str):
            return value.strip().lower() in ("true", "yes", "1")
        return value


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classify the support ticket. Return JSON only, no extra text, matching "
            'exactly this shape: {{"sentiment": "positive|neutral|negative|abusive", '
            '"category": "refund_request|subscription_cancellation|login_access|'
            'troubleshooting|abusive_content|other", "requires_more_info": true or '
            'false (a JSON boolean), "missing_fields": ["..."]}}. Pick the category '
            "the ticket is fundamentally about, even if the tone is hostile (e.g. an "
            "angry refund request is still refund_request, not abusive_content, unless "
            "the message contains no substantive request at all). Set "
            "requires_more_info=true only if the ticket lacks details needed to act on "
            "it (e.g. no account/order identifier, no error description, vague "
            "symptom) -- do not ask for more info just because extra detail could be "
            "helpful.",
        ),
        ("human", "Subject: {subject}\nMessage: {message}"),
    ]
)


def classify_ticket(ticket: Ticket, llm, settings: Settings) -> ClassificationResult:
    json_llm = llm.bind(response_format={"type": "json_object"})
    chain = _PROMPT | json_llm
    response = chain.invoke({"subject": ticket.subject, "message": ticket.message})
    data = json.loads(response.content)
    return ClassificationResult.model_validate(data)
