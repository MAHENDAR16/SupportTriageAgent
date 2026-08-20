from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: str
    content: str


class Ticket(BaseModel):
    ticket_id: str
    customer_id: str
    subject: str
    message: str
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    priority: str = "medium"
    category: str = "other"

    order_id: str | None = None
    account_id: str | None = None
    subscription_id: str | None = None
    days_since_purchase: int | None = None
    previous_refund_request_count: int = 0
    days_since_last_refund_request: int | None = None
