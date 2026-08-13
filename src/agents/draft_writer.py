from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import RetrievedChunk
from src.models.ticket import Ticket

_PROMPT = ChatPromptTemplate.from_messages(
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


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no relevant knowledge base content retrieved)"
    return "\n\n".join(f"[source: {c['source']}]\n{c['text']}" for c in chunks)


def draft_answer(ticket: Ticket, retrieved_chunks: list[RetrievedChunk], llm) -> str:
    chain = _PROMPT | llm
    response = chain.invoke(
        {
            "context": _format_context(retrieved_chunks),
            "subject": ticket.subject,
            "message": ticket.message,
        }
    )
    return response.content
