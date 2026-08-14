from __future__ import annotations

import json
import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from src.graph.state import RetrievedChunk
from src.models.ticket import Ticket

CITATION_PATTERN = re.compile(r"\[source:\s*([\w\-. ]+?)\]", re.IGNORECASE)


def extract_cited_sources(draft_reply: str) -> list[str]:
    return [match.strip() for match in CITATION_PATTERN.findall(draft_reply)]


def compute_groundedness(retrieved_chunks: list[RetrievedChunk]) -> float:
    if not retrieved_chunks:
        return 0.0
    return max(chunk["score"] for chunk in retrieved_chunks)


def find_fabricated_citations(draft_reply: str, retrieved_chunks: list[RetrievedChunk]) -> list[str]:
    """Citations in the draft that don't correspond to an actually retrieved
    source -- forces ESCALATE regardless of the similarity score."""
    cited = extract_cited_sources(draft_reply)
    valid_sources = {chunk["source"] for chunk in retrieved_chunks}
    return [source for source in cited if source not in valid_sources]


class GroundednessJudgment(BaseModel):
    score: float
    unsupported_claims: list[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def _coerce_score(cls, value):
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return value


_DRAFT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a support draft-writer. You may ONLY state policy facts that "
            "appear in the CONTEXT below, with a source citation. If the context "
            "does not answer the customer's question, say plainly that the "
            "relevant policy could not be verified and recommend escalation. "
            "Never invent policy details. Write a draft reply (not sent to the "
            "customer) citing sources like [source: refund_policy.md].",
        ),
        (
            "human",
            "Context:\n{context}\n\nCustomer subject: {subject}\nCustomer message: {message}",
        ),
    ]
)

_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given the DRAFT and the CONTEXT, score 0-1 how well every factual "
            "claim in DRAFT is supported by CONTEXT. Flag any unsupported claim "
            "as a short phrase. A draft that plainly states policy could not be "
            "verified and recommends escalation, with no invented policy "
            "details, should score close to 1.0 -- it isn't making unsupported "
            "claims, it's correctly declining to. Return JSON only, no extra "
            'text, matching exactly this shape: {{"score": <float 0-1>, '
            '"unsupported_claims": ["..."]}}.',
        ),
        ("human", "CONTEXT:\n{context}\n\nDRAFT:\n{draft}"),
    ]
)


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no relevant knowledge base content retrieved)"
    return "\n\n".join(f"[source: {c['source']}]\n{c['text']}" for c in chunks)


def draft_answer(ticket: Ticket, retrieved_chunks: list[RetrievedChunk], llm) -> str:
    chain = _DRAFT_PROMPT | llm
    response = chain.invoke(
        {
            "context": _format_context(retrieved_chunks),
            "subject": ticket.subject,
            "message": ticket.message,
        }
    )
    return response.content


def judge_groundedness(draft_reply: str, retrieved_chunks: list[RetrievedChunk], llm) -> GroundednessJudgment:
    json_llm = llm.bind(response_format={"type": "json_object"})
    chain = _JUDGE_PROMPT | json_llm
    response = chain.invoke({"context": _format_context(retrieved_chunks), "draft": draft_reply})
    data = json.loads(response.content)
    return GroundednessJudgment.model_validate(data)
