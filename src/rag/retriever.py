from __future__ import annotations

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config.settings import Settings
from src.graph.graph_state import RetrievedChunk
from src.rag.kb_loader import load_kb_chunks


class Retriever:
    """In-memory FAISS index over the knowledge base. Rebuilt on every
    process start -- cheap at ~5 files / ~30 chunks, avoids stale-index bugs.
    """

    # Embeds all KB chunks with the sentence-transformers model and loads
    # them into a flat inner-product FAISS index for cosine-similarity search.
    def __init__(self, chunks: list[dict], model_name: str) -> None:
        self._chunks = chunks
        self._model = SentenceTransformer(model_name)
        texts = [c["text"] for c in chunks]
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype="float32")
        self._index = faiss.IndexFlatIP(embeddings.shape[1])
        if len(chunks):
            self._index.add(embeddings)

    # Embeds the query and searches the FAISS index for the top-k most
    # similar chunks, returning them with their source and similarity score.
    def retrieve(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        if not self._chunks:
            return []
        query_embedding = self._model.encode([query], normalize_embeddings=True)
        query_embedding = np.asarray(query_embedding, dtype="float32")
        scores, indices = self._index.search(query_embedding, min(k, len(self._chunks)))
        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self._chunks[idx]
            results.append({"source": chunk["source"], "text": chunk["text"], "score": float(score)})
        return results


# Factory that loads the KB chunks and wraps them in a freshly-built Retriever.
# Called once per process at graph-construction time.
def build_retriever(settings: Settings) -> Retriever:
    chunks = load_kb_chunks(settings)
    return Retriever(chunks, settings.embeddings_model)
