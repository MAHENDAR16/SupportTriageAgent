from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config.settings import get_settings  # noqa: E402
from src.graph.build_graph import build_default_deps, build_graph  # noqa: E402
from src.main import load_tickets  # noqa: E402


def _load_golden(settings) -> dict[str, dict]:
    raw = json.loads(settings.golden_dataset_path.read_text(encoding="utf-8"))
    return {entry["ticket_id"]: entry for entry in raw}


def _assert_one_to_one(tickets, golden: dict[str, dict]) -> None:
    ticket_ids = {t.ticket_id for t in tickets}
    golden_ids = set(golden.keys())
    missing_golden = ticket_ids - golden_ids
    orphan_golden = golden_ids - ticket_ids
    if missing_golden or orphan_golden:
        raise AssertionError(
            "Tickets and golden dataset are not 1:1. "
            f"Tickets missing a golden entry: {sorted(missing_golden)}. "
            f"Golden entries with no matching ticket: {sorted(orphan_golden)}."
        )


def run_eval() -> dict:
    settings = get_settings()
    tickets = load_tickets(settings)
    golden = _load_golden(settings)
    _assert_one_to_one(tickets, golden)

    deps = build_default_deps(auto_approve=True, settings=settings)
    graph = build_graph(deps)

    per_ticket = []
    correct_routes = 0
    auto_resolve_count = 0
    auto_resolve_with_citation = 0
    fabricated_citation_count = 0

    for ticket in tickets:
        final_state = graph.invoke({"ticket": ticket})
        expected_route = golden[ticket.ticket_id]["expected_route"]
        actual_route = final_state.get("route_decision")
        route_correct = actual_route == expected_route
        correct_routes += int(route_correct)

        has_citation = bool(final_state.get("draft_reply")) and "[source:" in final_state.get("draft_reply", "")
        fabricated = final_state.get("fabricated_citations") or []

        if actual_route == "AUTO_RESOLVE":
            auto_resolve_count += 1
            if has_citation:
                auto_resolve_with_citation += 1
        if fabricated:
            fabricated_citation_count += 1

        per_ticket.append(
            {
                "ticket_id": ticket.ticket_id,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "route_correct": route_correct,
                "route_reason": final_state.get("route_reason"),
                "groundedness_score": final_state.get("groundedness_score"),
                "has_citation": has_citation,
                "fabricated_citations": fabricated,
            }
        )

    total = len(tickets)
    route_accuracy = correct_routes / total if total else 0.0
    citation_presence_rate = (
        auto_resolve_with_citation / auto_resolve_count if auto_resolve_count else 1.0
    )
    fabricated_citation_rate = fabricated_citation_count / total if total else 0.0

    summary = {
        "total_tickets": total,
        "correct_routes": correct_routes,
        "route_accuracy": route_accuracy,
        "route_accuracy_target": 0.90,
        "route_accuracy_pass": route_accuracy >= 0.90,
        "auto_resolve_count": auto_resolve_count,
        "citation_presence_rate": citation_presence_rate,
        "citation_presence_target": 1.0,
        "citation_presence_pass": citation_presence_rate >= 1.0,
        "fabricated_citation_rate": fabricated_citation_rate,
        "fabricated_citation_target": 0.0,
        "fabricated_citation_pass": fabricated_citation_rate <= 0.0,
    }
    summary["overall_pass"] = (
        summary["route_accuracy_pass"]
        and summary["citation_presence_pass"]
        and summary["fabricated_citation_pass"]
    )

    report = {"summary": summary, "tickets": per_ticket}
    report_path = settings.evaluation_reports_dir / "eval_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _print_report(report: dict) -> None:
    summary = report["summary"]
    print(f"{'ticket_id':10} {'expected':12} {'actual':12} {'ok':4} reason")
    for row in report["tickets"]:
        ok = "PASS" if row["route_correct"] else "FAIL"
        print(f"{row['ticket_id']:10} {row['expected_route']:12} {row['actual_route']:12} {ok:4} {row['route_reason']}")
    print()
    print(f"Route accuracy:      {summary['route_accuracy']:.1%} "
          f"({summary['correct_routes']}/{summary['total_tickets']}), "
          f"target >= {summary['route_accuracy_target']:.0%} "
          f"[{'PASS' if summary['route_accuracy_pass'] else 'FAIL'}]")
    print(f"Citation presence:   {summary['citation_presence_rate']:.1%} of AUTO_RESOLVE drafts, "
          f"target >= {summary['citation_presence_target']:.0%} "
          f"[{'PASS' if summary['citation_presence_pass'] else 'FAIL'}]")
    print(f"Fabricated citation: {summary['fabricated_citation_rate']:.1%}, "
          f"target <= {summary['fabricated_citation_target']:.0%} "
          f"[{'PASS' if summary['fabricated_citation_pass'] else 'FAIL'}]")
    print()
    print(f"OVERALL: {'PASS' if summary['overall_pass'] else 'FAIL'}")


if __name__ == "__main__":
    report = run_eval()
    _print_report(report)
    sys.exit(0 if report["summary"]["overall_pass"] else 1)
