# Support Triage Agent — Evaluation Report

**Source:** `data/evaluation/run_eval.py` against `data/evaluation/golden_dataset.json` (22 golden tickets, 1:1 with `data/synthetic_tickets.json`)
**Data captured:** 2026-08-14 (last successful live run — see *Regeneration* note below)
**Raw data:** [`eval_report.json`](./eval_report.json) in this same folder

## 1. Summary

| Metric | Result | Target | Status |
|---|---|---|---|
| Route accuracy | **100.0%** (22/22) | ≥ 90% | ✅ PASS |
| Citation presence (AUTO_RESOLVE drafts) | **100.0%** (6/6) | ≥ 100% | ✅ PASS |
| Fabricated citation rate | **0.0%** (0/22) | ≤ 0% | ✅ PASS |
| **Overall** | | | ✅ **PASS** |

Every ticket's `route_decision` matched the golden-labeled `expected_route`, every `AUTO_RESOLVE` reply cited a policy source (`[source: ...]`), and no citations pointed to nonexistent policy text.

## 2. Route breakdown

| Route | Count | Tickets |
|---|---|---|
| `AUTO_RESOLVE` | 6 | TCK-1001, 1004, 1011, 1016, 1019, 1022 |
| `ESCALATE` | 7 | TCK-1002, 1003, 1008, 1015, 1017, 1018, 1020 |
| `ASK_INFO` | 6 | TCK-1005, 1006, 1007, 1012, 1013, 1014 |
| `REFUSE` | 3 | TCK-1009, 1010, 1021 |

Escalation reasons split across `refund_outside_window` (3), `low_groundedness` (2), `repeat_refund_request_within_window` (1), and `policy_mandated_escalation_keywords` (1) — i.e. escalations were driven by a mix of the deterministic refund-window rules and the LLM-judge groundedness gate, not one dominant path.

## 3. Groundedness scores

Phase-1 retrieval-similarity groundedness (`groundedness_score`), across all 22 tickets:

- **Mean:** 0.469
- **Min:** 0.172 (TCK-1017 → correctly routed to `ESCALATE` via `low_groundedness`)
- **Max:** 0.652 (TCK-1019 → `AUTO_RESOLVE`)

Low-scoring tickets (TCK-1009, 1017, 1018, 1021) were routed to `ESCALATE`/`REFUSE` rather than auto-resolved, which is the intended behavior — the confidence-recheck loop (`src/graph/nodes/confidence_recheck.py`) is filtering on this score before letting a low-groundedness draft reach a customer.
