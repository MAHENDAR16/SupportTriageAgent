from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.audit.logger import AuditLogger
from src.config.settings import Settings
from src.persistence.db import ReviewStore
from src.rag.retriever import Retriever


@dataclass
class GraphDeps:
    settings: Settings
    llm: Any
    retriever: Retriever
    audit_logger: AuditLogger
    auto_approve: bool = False
    # When False and auto_approve is also False, hitl_gate persists the
    # ticket as PENDING_REVIEW instead of blocking on an interactive CLI
    # prompt -- the mode used when a UI will review the queue asynchronously.
    interactive: bool = True
    review_store: Optional[ReviewStore] = None
