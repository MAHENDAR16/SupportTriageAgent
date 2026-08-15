from __future__ import annotations

from src.config.settings import Settings
from src.graph.graph_state import RetrievedChunk
from src.rag.retriever import Retriever, build_retriever


class RAGAgent:
    """Orchestrates retrieval-augmented generation: loads knowledge base,
    builds vector index, and performs similarity search."""

    # Stores the pre-built Retriever instance so retrieve() can delegate to it.
    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    # Delegates to the underlying Retriever's similarity search.
    # Returns the top-k knowledge base chunks matching the query.
    def retrieve(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        """Retrieve top-k knowledge base chunks matching the query."""
        return self.retriever.retrieve(query, k=k)


# Factory that builds a Retriever from Settings and wraps it in a RAGAgent.
# Used wherever the RAG agent needs to be constructed with a loaded KB.
def build_rag_agent(settings: Settings) -> RAGAgent:
    """Factory to construct and initialize the RAG agent with loaded KB."""
    retriever = build_retriever(settings)
    return RAGAgent(retriever)
