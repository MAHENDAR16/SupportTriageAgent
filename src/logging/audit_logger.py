from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.graph.state import AuditLogEntry

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only audit log with optional Arize AI integration.
    Logs all AI decisions to both local JSONL file and Arize for compliance/monitoring.
    No update/delete methods are exposed, by design."""

    def __init__(self, path: Path, arize_enabled: bool = False) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.arize_enabled = arize_enabled
        self._arize_client = None

        if arize_enabled:
            self._init_arize()

    def _init_arize(self) -> None:
        """Initialize Arize client if credentials are available in environment."""
        try:
            from arize.utils.types import Schema, Embedding
            from arize import Client

            api_key = os.getenv("ARIZE_API_KEY")
            api_url = os.getenv("ARIZE_API_URL", "https://api.arize.com/v1")

            if not api_key:
                logger.warning("ARIZE_API_KEY not set; Arize logging disabled")
                self.arize_enabled = False
                return

            self._arize_client = Client(api_key=api_key, api_url=api_url)
            logger.info("Arize client initialized successfully")
        except ImportError:
            logger.warning("arize package not installed; Arize logging disabled")
            self.arize_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Arize client: {e}")
            self.arize_enabled = False

    def log(
        self,
        ticket_id: str,
        node: str,
        output: dict,
        actor: str = "system",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an audit entry to both local file and Arize.

        Args:
            ticket_id: Unique ticket identifier
            node: Pipeline node name (e.g. 'sentiment_policy_check', 'route')
            output: Output data from the node
            actor: Who made the decision ('system', 'reviewer:cli', 'reviewer:ui')
            metadata: Optional additional context
        """
        entry: AuditLogEntry = {
            "ticket_id": ticket_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": node,
            "output": output,
            "actor": actor,
        }

        # Write to local JSONL file
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Log to Arize if enabled
        if self.arize_enabled and self._arize_client:
            self._log_to_arize(ticket_id, node, output, actor, metadata)

    def _log_to_arize(
        self,
        ticket_id: str,
        node: str,
        output: dict,
        actor: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Send audit entry to Arize for centralized logging and monitoring."""
        try:
            # Flatten output dict for Arize attributes
            attributes = {
                "ticket_id": ticket_id,
                "node": node,
                "actor": actor,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add output fields as attributes
            for key, value in output.items():
                if isinstance(value, (str, int, float, bool)):
                    attributes[f"output_{key}"] = value

            # Send custom event to Arize
            self._arize_client.log_validation(
                model_id="support_triage_agent",
                model_version="1.0",
                data={
                    "attributes": attributes,
                    "prediction_id": ticket_id,
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )
        except Exception as e:
            logger.error(f"Failed to log to Arize: {e}")
