from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import Settings


# Reads every .md file under kb_dir and splits it into overlapping chunks
# (500 chars, 50 overlap), each tagged with its source filename.
def load_kb_chunks(settings: Settings) -> list[dict]:
    """Load every markdown file in the knowledge base, split into chunks
    tagged with their source filename."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks: list[dict] = []
    for path in sorted(settings.kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for piece in splitter.split_text(text):
            chunks.append({"source": path.name, "text": piece})
    return chunks
