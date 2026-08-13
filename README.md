# SupportTriageAgent

An AI agent that triages customer support tickets against a markdown policy knowledge base and drafts a response — it never sends anything to a customer. Every draft goes through a human-in-the-loop approval gate. See `support_triage_agent_implementation_plan.md` for the full architecture and phased build plan.

Status: Phase 0 (project setup), Phase 1 (MVP linear RAG + single-pass routing), and Phase 2 (confidence-recheck refinement loop + Streamlit reviewer UI + SQLite persistence) are implemented. Phase 3+ (multi-turn memory, category-specialized agents, production monitoring) is not built yet.

Note on Phase 2's reviewer UI: the source doc lists a FastAPI layer to sit between the graph and the UI. The Streamlit app instead calls the graph and persistence modules directly in-process — same reasoning as Phase 1 deferring FastAPI: the UI runs locally, single-process, so a REST hop to itself adds infrastructure without adding capability. The persistence layer (`src/persistence/`) is written as a standalone module so a future FastAPI layer could sit on top of it without rework.

## Setup

```bash
python3 -m venv .supportvenv
source .supportvenv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY
```

## Run

```bash
# Verify Groq connectivity and the deterministic rule layer
pytest tests/test_groq_connection.py tests/test_rules.py -v

# Process a single ticket (prints and writes outputs/results/<ticket_id>.json)
python -m src.main --ticket TCK-1001

# Process every ticket in data/synthetic_tickets.json, auto-approving the
# HITL gate (skips the interactive reviewer prompt; use without
# --auto-approve to review each draft at the CLI, or --queue to leave items
# pending in the reviewer DB for the Streamlit UI instead)
python -m src.main --all --auto-approve

# Run the golden-dataset evaluation harness (route accuracy, citation
# presence, fabricated-citation rate) -- writes evaluation/eval_report.json
python evaluation/run_eval.py

# Populate the reviewer queue, then launch the Streamlit reviewer UI
python -m src.main --all --queue
streamlit run ui/streamlit_app.py

# Full test suite (includes an end-to-end graph smoke test that calls the
# real Groq API -- the rest of the suite mocks LLM calls and runs offline)
pytest tests/ -v
```

Every ticket run appends to `outputs/audit_log.jsonl` (append-only, one entry per graph node per ticket) and writes the final `GraphState` to `outputs/results/<ticket_id>.json`. Reviewer queue items and decisions (Approve/Reject/Edit/Regenerate/Escalate) persist to `outputs/triage.db` (SQLite; swap to Postgres later by pointing `DATABASE_URL`-style config at it -- the `ReviewStore` interface doesn't change).

### Phase 2 architecture notes

- **Confidence-recheck loop** (`src/graph/nodes/confidence_recheck.py`): only reached when `route_decision == AUTO_RESOLVE`. Runs a second, stricter LLM-as-judge check on the actual drafted text (distinct from Phase 1's cheap retrieval-similarity gate in `route_decision`). A failing judgment with retries remaining loops back to `rag_retrieve` with a reformulated query (the unsupported claims, plus a wider `k`); once `max_retrieval_attempts` is exhausted, it forces `ESCALATE` with reason `low_confidence_after_retries` rather than looping forever.
- **Reviewer actions**: the full Approve/Reject/Edit/Regenerate/Escalate set from the source doc's HITL design is implemented in `src/services/review_service.py`. Regenerate marks the old queue row `SUPERSEDED` and re-runs the graph, producing a fresh pending row (`regenerate_count` tracks how many times a ticket has been redrafted).
