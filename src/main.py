from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config.settings import Settings, get_settings
from src.graph.build_graph import build_default_deps, build_graph
from src.models.ticket import Ticket


# Reads the synthetic tickets JSON dataset and parses each entry into a
# validated Ticket model.
def load_tickets(settings: Settings) -> list[Ticket]:
    raw = json.loads(settings.tickets_path.read_text(encoding="utf-8"))
    return [Ticket(**t) for t in raw]


# Converts final graph state into a JSON-safe dict, expanding the embedded
# Ticket model (via model_dump()) so it serializes cleanly.
def _serialize_state(state: dict) -> dict:
    result = dict(state)
    ticket = result.get("ticket")
    if isinstance(ticket, Ticket):
        result["ticket"] = ticket.model_dump()
    return result


# Runs one ticket through the compiled graph, then writes both the full
# result JSON and the plain-text draft reply to their respective output dirs.
def run_ticket(graph, ticket: Ticket, results_dir: Path, drafted_replies_dir: Path) -> dict:
    final_state = graph.invoke({"ticket": ticket})
    serialized = _serialize_state(final_state)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{ticket.ticket_id}.json").write_text(
        json.dumps(serialized, indent=2, default=str), encoding="utf-8"
    )
    drafted_replies_dir.mkdir(parents=True, exist_ok=True)
    (drafted_replies_dir / f"{ticket.ticket_id}.txt").write_text(
        serialized.get("draft_reply") or "", encoding="utf-8"
    )
    return serialized


# CLI entry point: parses --ticket/--all/--auto-approve/--queue flags, builds
# the graph, and runs each selected ticket through run_ticket() in sequence.
def main() -> None:
    parser = argparse.ArgumentParser(description="Run the support triage agent over tickets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", help="Process a single ticket by ID (e.g. TCK-1001)")
    group.add_argument("--all", action="store_true", help="Process every ticket in the dataset")
    parser.add_argument(
        "--auto-approve", action="store_true", help="Bypass the interactive HITL prompt (batch/eval runs)"
    )
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Leave processed tickets as PENDING_REVIEW in the reviewer DB instead of "
        "prompting at the CLI -- populates the queue for the Streamlit reviewer UI",
    )
    args = parser.parse_args()

    settings = get_settings()
    deps = build_default_deps(
        auto_approve=args.auto_approve, interactive=not args.queue, settings=settings
    )
    graph = build_graph(deps)
    results_dir = settings.results_dir
    drafted_replies_dir = settings.drafted_replies_dir

    tickets = load_tickets(settings)
    if args.ticket:
        tickets = [t for t in tickets if t.ticket_id == args.ticket]
        if not tickets:
            raise SystemExit(f"No ticket found with id {args.ticket}")

    for ticket in tickets:
        result = run_ticket(graph, ticket, results_dir, drafted_replies_dir)
        print(f"{ticket.ticket_id}: {result.get('route_decision')} ({result.get('route_reason')})")


if __name__ == "__main__":
    main()
