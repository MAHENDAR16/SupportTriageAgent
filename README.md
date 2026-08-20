# SupportTriageAgent

An AI agent that triages customer support tickets against a markdown policy knowledge base and drafts a response — it never sends anything to a customer. Every draft goes through a human-in-the-loop approval gate. See `support_triage_agent_implementation_plan.md` for the full architecture and phased build plan.

Status: Phase 0 (project setup), Phase 1 (MVP linear RAG + single-pass routing), and Phase 2 (confidence-recheck refinement loop + Streamlit reviewer UI + SQLite persistence) are implemented. Phase 3+ (multi-turn memory, category-specialized agents, production monitoring) is not built yet.

Note on Phase 2's reviewer UI: the source doc lists a FastAPI layer to sit between the graph and the UI. The Streamlit app instead calls the graph and persistence modules directly in-process — same reasoning as Phase 1 deferring FastAPI: the UI runs locally, single-process, so a REST hop to itself adds infrastructure without adding capability. The persistence layer (`src/persistence/`) is written as a standalone module so a future FastAPI layer could sit on top of it without rework.

## Setup

```bash
python3 -m venv .supportvenv
source .supportvenv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY (optionally ARIZE_API_KEY/ARIZE_SPACE_ID for tracing)
```

## Run

All commands assume the repo root as the working directory (`ModuleNotFoundError: No module named 'src'` means you're not there) and the venv activated.

```bash
# --- Verify setup (no Groq quota needed) ---

# Config loads and reads categories/model from app_config.yaml + .env
python -c "from src.config.settings import get_settings; s = get_settings(); print(f'{len(s.categories)} categories, model={s.groq_model}, arize_enabled={s.arize_enabled}')"

# Deterministic rule layer (refund window, required fields, abuse detection)
pytest tests/test_rules.py -v

# SQLite persistence + reviewer-action flows (Approve/Reject/Edit/Regenerate/Escalate) -- LLM calls mocked, runs offline
pytest tests/test_persistence.py tests/test_review_service.py -v

# --- Verify Groq connectivity (needs GROQ_API_KEY in .env) ---
pytest tests/test_groq_connection.py -v

# --- Run tickets through the agent (needs Groq quota) ---

# Single ticket -- prints route_decision and writes outputs/results/<ticket_id>.json
python -m src.main --ticket TCK-1001

# Every ticket in data/synthetic_tickets.json, auto-approving the HITL gate
# (skips the interactive reviewer prompt; omit --auto-approve to review each
# draft at the CLI instead, or use --queue below to route to the Streamlit UI)
python -m src.main --all --auto-approve

# Golden-dataset evaluation harness (route accuracy, citation presence,
# fabricated-citation rate) -- writes outputs/evaluation_reports/eval_report.json
python data/evaluation/run_eval.py

# --- Reviewer UI ---

# Populate the reviewer queue (each ticket lands PENDING_REVIEW instead of
# blocking on input), then launch the Streamlit reviewer UI
python -m src.main --all --queue
streamlit run ui/streamlit_app.py
# -> http://localhost:8501 -- Approve/Reject/Edit/Regenerate/Escalate each
#    queued ticket; only "Run agent" and "Regenerate" need Groq quota

# --- Notebooks (read pre-generated outputs/*, don't need GROQ_API_KEY except langgraph_flow_demo.ipynb) ---
jupyter notebook notebooks/
# or: jupyter lab notebooks/

# --- Full test suite (includes an end-to-end graph smoke test that calls the
# real Groq API -- the rest of the suite mocks LLM calls and runs offline) ---
pytest tests/ -v
```

Every ticket run appends to `outputs/audit_logs/audit_log.jsonl` (append-only, one entry per graph node per ticket) and writes the final `GraphState` to `outputs/results/<ticket_id>.json`. Reviewer queue items and decisions (Approve/Reject/Edit/Regenerate/Escalate) persist to `outputs/databases/triage.db` (SQLite; swap to Postgres later by pointing `DATABASE_URL`-style config at it -- the `ReviewStore` interface doesn't change). Customer conversation-thread history persists to `outputs/databases/threads.db`. See `DEMO_COMMANDS.md` for expected output at each step and a troubleshooting table (missing `.env`, Groq 429s, locked SQLite files, etc.).

### Phase 2 architecture notes

- **Confidence-recheck loop** (`src/graph/nodes/confidence_recheck.py`): only reached when `route_decision == AUTO_RESOLVE`. Runs a second, stricter LLM-as-judge check on the actual drafted text (distinct from Phase 1's cheap retrieval-similarity gate in `route_decision`). A failing judgment with retries remaining loops back to `rag_retrieve` with a reformulated query (the unsupported claims, plus a wider `k`); once `max_retrieval_attempts` is exhausted, it forces `ESCALATE` with reason `low_confidence_after_retries` rather than looping forever.
- **Reviewer actions**: the full Approve/Reject/Edit/Regenerate/Escalate set from the source doc's HITL design is implemented in `src/hitl/reviewer_actions.py`. Regenerate marks the old queue row `SUPERSEDED` and re-runs the graph, producing a fresh pending row (`regenerate_count` tracks how many times a ticket has been redrafted).
