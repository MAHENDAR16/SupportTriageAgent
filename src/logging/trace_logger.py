from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TraceLogger:
    """Distributed tracing logger for monitoring graph pipeline execution.
    Logs pipeline traces to both local file and Arize for performance monitoring."""

    def __init__(self, path: Path, arize_enabled: bool = False) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.arize_enabled = arize_enabled
        self._arize_client = None

        if arize_enabled:
            self._init_arize()

    def _init_arize(self) -> None:
        """Initialize Arize client for trace logging."""
        try:
            from arize import Client

            api_key = os.getenv("ARIZE_API_KEY")
            api_url = os.getenv("ARIZE_API_URL", "https://api.arize.com/v1")

            if not api_key:
                logger.warning("ARIZE_API_KEY not set; Arize trace logging disabled")
                self.arize_enabled = False
                return

            self._arize_client = Client(api_key=api_key, api_url=api_url)
            logger.info("Arize trace client initialized")
        except ImportError:
            logger.warning("arize package not installed; Arize trace logging disabled")
            self.arize_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Arize trace client: {e}")
            self.arize_enabled = False

    def log_trace(
        self,
        ticket_id: str,
        trace_name: str,
        start_time: float,
        end_time: float,
        node_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log a single trace/span to both local file and Arize.

        Args:
            ticket_id: Unique ticket identifier
            trace_name: Name of the trace (e.g. 'pipeline_execution')
            start_time: Start timestamp (seconds since epoch)
            end_time: End timestamp (seconds since epoch)
            node_name: Name of the pipeline node
            inputs: Input data to the node
            outputs: Output data from the node
            metadata: Optional additional context
        """
        duration_ms = (end_time - start_time) * 1000

        trace_entry = {
            "ticket_id": ticket_id,
            "trace_name": trace_name,
            "node_name": node_name,
            "start_time": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            "end_time": datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "inputs": self._serialize_data(inputs),
            "outputs": self._serialize_data(outputs),
            "metadata": metadata or {},
        }

        # Write to local JSONL file
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace_entry) + "\n")

        # Log to Arize if enabled
        if self.arize_enabled and self._arize_client:
            self._log_trace_to_arize(ticket_id, trace_entry)

    def _serialize_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Safely serialize data for JSON logging."""
        serialized = {}
        for key, value in data.items():
            try:
                # Test if serializable
                json.dumps(value)
                serialized[key] = value
            except (TypeError, ValueError):
                # Fallback to string representation
                serialized[key] = str(value)
        return serialized

    def _log_trace_to_arize(self, ticket_id: str, trace_entry: dict[str, Any]) -> None:
        """Send trace to Arize for distributed tracing visualization."""
        try:
            # Build attributes from trace
            attributes = {
                "ticket_id": ticket_id,
                "node_name": trace_entry["node_name"],
                "duration_ms": trace_entry["duration_ms"],
                "trace_name": trace_entry["trace_name"],
            }

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
            logger.error(f"Failed to log trace to Arize: {e}")

    def start_span(self, span_name: str) -> float:
        """Start a timing span. Returns start time for use with end_span."""
        return time.time()

    def end_span(
        self,
        ticket_id: str,
        span_name: str,
        start_time: float,
        node_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """End a timing span and log the trace."""
        end_time = time.time()
        self.log_trace(
            ticket_id=ticket_id,
            trace_name=span_name,
            start_time=start_time,
            end_time=end_time,
            node_name=node_name,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
        )
