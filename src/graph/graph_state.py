from __future__ import annotations

from typing import Optional, TypedDict

from src.models.ticket import Ticket


class RetrievedChunk(TypedDict):
    source: str
    text: str
    score: float


class GraphState(TypedDict, total=False):
    ticket: Ticket
    sentiment: str                      # positive | neutral | negative | abusive
    detected_category: str              # refund_request | subscription_cancellation | ...
    requires_more_info: bool
    missing_fields: list[str]
    abuse_detected: bool
    conversation_context: str           # formatted conversation history for LLM context
    retrieved_chunks: list[RetrievedChunk]
    draft_reply: str
    fabricated_citations: list[str]
    route_decision: str                 # AUTO_RESOLVE | ESCALATE | REFUSE | ASK_INFO
    route_reason: str
    confidence_score: float
    groundedness_score: float           # retrieval-similarity score (Phase 1 first-pass gate)
    retrieval_attempts: int
    llm_groundedness_score: float       # LLM-as-judge score (Phase 2 stricter re-check)
    unsupported_claims: list[str]
    llm_groundedness_passed: bool
    query_reformulation_hint: str
    reviewer_action: Optional[str]
    reviewer_comments: Optional[str]
    review_id: Optional[int]


class AuditLogEntry(TypedDict):
    ticket_id: str
    timestamp: str
    node: str
    output: dict
    actor: str


class ReviewerRecord(TypedDict):
    ticket_id: str
    draft_reply: str
    route_decision: str
    confidence_score: float
    retrieved_sources: list[str]
    reviewer_action: Optional[str]
    reviewer_comments: Optional[str]
