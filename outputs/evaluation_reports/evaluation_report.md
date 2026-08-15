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

## 4. Known instability (not a bug)

Per `PROGRESS.md`, **TCK-1001** has intermittently flipped between `AUTO_RESOLVE` (golden label) and `ESCALATE` (`low_confidence_after_retries`) across separate live runs. Root cause: `llm_temperature: 0.1` makes the `confidence_recheck` LLM-judge score non-deterministic, and TCK-1001's draft legitimately synthesizes two separate policy clauses (7-day eligibility + case-by-case annual-plan review), which the judge scores as borderline. This run scored it correctly (`AUTO_RESOLVE`, groundedness 0.557); a prior run on 2026-08-13 reported 95.5% (21/22) with TCK-1001 as the sole miss. Treat single-run accuracy numbers near 100% as expected variance on this one ticket rather than a regression if it dips slightly in a future run.

## 5. Regeneration

This report reflects the last successful live run recorded in the repo (`outputs/evaluation_reports/eval_report.json`, 2026-08-14). A fresh run was attempted while producing this report but failed on Groq's free-tier daily token quota (100k TPD, ~99.9k already used today):

```
groq.RateLimitError: 429 - tokens per day (TPD): Limit 100000, Used 99853
```

To regenerate once the quota resets:

```bash
python data/evaluation/run_eval.py
```

This writes `outputs/evaluation_reports/eval_report.json` directly (per `config/app_config.yaml`'s `evaluation_reports_dir`) — re-running will overwrite the JSON in this folder with fresh numbers. Update this Markdown summary by hand afterward if the results change materially.
