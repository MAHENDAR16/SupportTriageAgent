from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.graph.state import AuditLogEntry


class AuditLogger:
    """Append-only JSONL writer. No update/delete methods are exposed, by
    design -- the audit log must support compliance review of every AI
    decision. LLM-call tracing (prompts/completions/latency) goes to Arize
    separately via src.observability.tracing's OpenTelemetry instrumentation."""

    # Stores the target JSONL path and ensures its parent directory exists.
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # Appends one timestamped audit entry (ticket, node, output, actor) as a
    # JSON line. No corresponding update/delete -- entries are immutable.
    def log(self, ticket_id: str, node: str, output: dict, actor: str = "system") -> None:
        entry: AuditLogEntry = {
            "ticket_id": ticket_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": node,
            "output": output,
            "actor": actor,
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
