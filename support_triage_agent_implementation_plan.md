# Support Ticket Triage & Resolution Agent — Implementation Plan

*Tech stack: LangChain + LangGraph, RAG over a Markdown knowledge base, HITL approval gate, Arize (or equivalent) for evaluation.*

---

## 1. Clarified Interpretation of the Problem Statement

### 1.1 Core Requirement
Build an AI agent that processes customer support tickets from a synthetic queue, checks them against a small policy/FAQ knowledge base (KB), and for each ticket decides one of four actions:

- **Auto-Resolve** — draft a policy-grounded reply that could close the ticket
- **Escalate** — hand off to a human specialist (policy ambiguous, refund out of window, repeat request, low grounding confidence, no policy found)
- **Refuse** — scripted, polite refusal (abuse/refund-abuse/out-of-scope requests)
- **Ask for More Information** — clarifying question when the ticket lacks details needed to act

### 1.2 Non-Negotiable Safety Principles (extracted from PDF)
| Principle | Implication for design |
|---|---|
| Replies are **drafts only**, never auto-sent | No customer-facing send capability anywhere in the system; HITL gate is mandatory on every path, including Auto-Resolve |
| Policies quoted **only from the KB** | The RAG layer is the *sole* source of policy text; no model-generated policy claims |
| If no policy is found, **state that and escalate** — never fabricate | A "no-groundedness" branch must exist in the graph, not just a prompt instruction |
| Refund abuse / abusive content → **scripted refusal** | These are handled as a deterministic rule/classifier, not left to free-form LLM judgment |
| Every draft goes through **human approval** (Approve / Reject / Edit / Regenerate / Escalate) | Persisted approval record, audit log, and reviewer action state machine |

### 1.3 Functional Requirements
1. Ingest a ticket (`ticket_id`, `customer_id`, `subject`, `message`, `conversation_history`, `priority`).
2. Run sentiment & policy classification (abuse detection, category detection, urgency).
3. Retrieve relevant KB chunks (RAG) and draft a grounded answer.
4. Route the ticket (LangGraph conditional edges) to Auto-Resolve / Escalate / Refuse / Ask-for-Info.
5. Re-check confidence/groundedness before finalizing route.
6. Present the draft to a human reviewer (HITL) via an approval queue.
7. Log every decision, retrieval, and reviewer action to an audit trail.

### 1.4 Non-Functional Requirements
- **Traceability**: every auto-resolve/escalate decision must be explainable (sources cited, confidence score, route rationale).
- **Determinism where it matters**: refusal and refund-abuse handling should not depend solely on LLM judgment — back with rules/classifiers.
- **Auditability**: immutable audit log per ticket (decision, retrieved sources, reviewer action, timestamps).
- **Latency**: end-to-end draft generation should complete in a few seconds (single ticket, not batch) to keep the review queue responsive.
- **Extensibility**: KB, routing rules, and ticket categories should be config-driven (`config/*.yaml`), not hardcoded.
- **No PII leakage**: customer data stays within the pipeline; nothing is sent to external logging/eval services without redaction.

---

## 2. System Architecture Overview

### 2.1 High-Level Component Diagram

```
                ┌─────────────────────┐
                │   Ticket Ingestion    │  (synthetic_tickets.json / API)
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │ Sentiment & Policy    │  (classifier node: abuse / category / urgency)
                │        Check          │
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │   RAG Retrieval       │──▶ Vector Store (FAISS/Chroma) ──▶ knowledge_base/*.md
                │   + Answer Draft      │
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │ LangGraph Route       │  conditional edges:
                │     Decision          │  auto_resolve / escalate / refuse / ask_info
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │ Confidence Re-check   │  groundedness + confidence threshold
                │        Loop            │  (loops back to retrieval if weak)
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │   HITL Approval       │  Approve / Reject / Edit / Regenerate / Escalate
                │        Gate            │
                └──────────┬───────────┘
                           ▼
                ┌─────────────────────┐
                │      Audit Log        │  append-only record per ticket
                └─────────────────────┘
```

### 2.2 Data Model

**Ticket** (input)
```json
{
  "ticket_id": "TCK-1001",
  "customer_id": "CUST-001",
  "subject": "Refund request for annual plan",
  "message": "I was charged for an annual plan yesterday...",
  "conversation_history": [],
  "priority": "medium",
  "category": "refund_request"  // may be inferred, not required on input
}
```

**GraphState** (LangGraph shared state, passed node-to-node)
```python
class GraphState(TypedDict):
    ticket: Ticket
    sentiment: str                 # positive / neutral / negative / abusive
    detected_category: str         # refund_request | subscription_cancellation | ...
    retrieved_chunks: list[dict]   # [{source, text, score}]
    draft_reply: str
    route_decision: str            # AUTO_RESOLVE | ESCALATE | REFUSE | ASK_INFO
    confidence_score: float
    groundedness_score: float
    retrieval_attempts: int        # for the refinement loop
    reviewer_action: str | None
    reviewer_comments: str | None
```

**Reviewer Record** (HITL output, persisted)
```json
{
  "ticket_id": "TCK-1001",
  "draft_reply": "...",
  "route_decision": "AUTO_RESOLVE",
  "confidence_score": 0.91,
  "retrieved_sources": ["refund_policy.md"],
  "reviewer_action": "APPROVED",
  "reviewer_comments": "Looks good."
}
```

**Audit Log Entry**
```json
{
  "ticket_id": "TCK-1001",
  "timestamp": "...",
  "node": "route_decision",
  "input_state_hash": "...",
  "output": {"route_decision": "ESCALATE", "reason": "no_policy_found"},
  "actor": "system" | "reviewer:<id>"
}
```

### 2.3 Components / Services

| Component | Responsibility | Tech |
|---|---|---|
| Ticket Ingestion Service | Load synthetic tickets / expose API endpoint for new tickets | FastAPI + Pydantic |
| Sentiment & Policy Classifier | Detect abuse, category, urgency | LangChain LLM call w/ structured output (or lightweight classifier for abuse detection as a deterministic first pass) |
| RAG Layer | Chunk, embed, store, retrieve KB content | LangChain `RecursiveCharacterTextSplitter`, embeddings model, FAISS/Chroma |
| Answer Draft Agent | Compose grounded draft citing sources | LangChain chain w/ retrieval-augmented prompt |
| LangGraph Orchestrator | State machine over the whole flow, conditional routing, refinement loop | LangGraph `StateGraph` |
| Confidence Re-check Node | Score groundedness (does answer text align with retrieved chunks?) and decide re-retrieve vs proceed | Custom scorer (LLM-as-judge or embedding similarity) |
| HITL Approval Service | Present drafts to reviewers, capture actions | FastAPI + simple UI (or CLI for MVP) |
| Audit Log Store | Append-only decision/action log | SQLite/Postgres (or JSONL files for MVP) |
| Evaluation Harness | Golden dataset regression tests, groundedness/route-accuracy metrics | Arize Phoenix (or LangSmith) + pytest |

### 2.4 Integration Points
- **LLM Orchestration**: LangChain for chains/prompts, LangGraph for the stateful multi-step workflow with branching and loops.
- **Retrieval**: local vector store (FAISS for MVP, swappable to Chroma/Azure AI Search later) over `data/knowledge_base/*.md`.
- **Storage**: relational store (Postgres in prod, SQLite in dev) for tickets, reviewer decisions, audit logs.
- **Auth** (for the HITL reviewer UI/API): basic auth or SSO stub for MVP; role-based access (reviewer vs admin) for later phases.
- **Model provider**: Anthropic/OpenAI-compatible via LangChain's model abstraction — keep provider swappable through `config/model_config.yaml`.

---

## 3. Phased Implementation Plan

### Phase 0 — Project Setup (0.5 week)
**Goals**: repo scaffolding, config system, synthetic data.
**Build**:
- Folder structure (per PDF's recommended layout: `config/`, `data/`, `src/graph/`, `src/agents/`, `outputs/`, `docs/`)
- `synthetic_tickets.json` (≥20 tickets spanning all 5 categories, including edge cases: abusive message, refund outside window, repeated refund request, vague ticket needing clarification)
- KB markdown files: `refund_policy.md`, `account_access_faq.md`, `subscription_policy.md`, `abusive_content_policy.md`, `troubleshooting_faq.md`
- `app_config.yaml`, `model_config.yaml`, `routing_rules.yaml`
**Success criteria**: tickets and KB load without error; config validated via Pydantic settings.

### Phase 1 — MVP: Linear RAG + Single-Pass Routing (1.5–2 weeks)
**Goals**: end-to-end path for one ticket — ingest → classify → retrieve → draft → route → HITL stub → log. No refinement loop yet.

**Key components**:
- LangGraph `StateGraph` with nodes: `ingest`, `sentiment_policy_check`, `rag_retrieve`, `draft_answer`, `route_decision`, `hitl_gate` (stubbed as auto-approve or CLI prompt), `audit_log`.
- Conditional edges from `route_decision`:
  - `groundedness_score >= threshold` and category matched → `AUTO_RESOLVE`
  - `no chunks retrieved` OR `groundedness_score < threshold` → `ESCALATE` (with "policy could not be verified" message)
  - `abuse_detected == True` → `REFUSE` (scripted response, bypasses LLM drafting)
  - `missing required fields` (e.g., no order/account ID for account issues) → `ASK_INFO`
- Refund-policy-specific rule layer (deterministic): 7-day window check, repeated-request check within 90 days — implemented as a plain Python function feeding the router, not left to the LLM.

**Data flow / story mapping**:
1. *As a reviewer*, I see a queue of drafted tickets with route + confidence + sources.
2. *As the system*, for every ticket I never send anything to the customer — output is always a draft record.
3. *As the system*, if I can't find a matching KB policy, I say so explicitly in the draft and route to Escalate.

**API contracts** (FastAPI, MVP):
```
POST /tickets            -> ingest ticket, returns ticket_id
POST /tickets/{id}/process -> runs the LangGraph flow, returns GraphState result
GET  /tickets/{id}       -> ticket + current state
GET  /queue              -> pending reviewer items
POST /tickets/{id}/review -> {action: APPROVE|REJECT|EDIT|REGENERATE|ESCALATE, comments, edited_reply?}
```

**Evaluation for this phase**:
- Golden dataset (`evaluation/golden_dataset.json`) with expected route per ticket.
- Route accuracy (% matching expected_routes.json).
- Manual spot-check that no reply is ever auto-sent (code review / static check: no email/SMS/API-send calls exist in the codebase).

**Success criteria**: ≥90% route accuracy on the golden set; 100% of AUTO_RESOLVE drafts cite at least one KB source; 0% fabricated policy citations.

### Phase 2 — Confidence Re-check Loop + Real HITL UI (1.5 weeks)
**Goals**: add the retrieval refinement loop and a real reviewer interface.

**Key components**:
- `confidence_recheck` node: if `groundedness_score` below threshold and `retrieval_attempts < max_attempts`, re-query retrieval with a reformulated query (LangGraph loop-back edge to `rag_retrieve`); otherwise force `ESCALATE`.
- Reviewer UI (simple React/Next.js or Streamlit) showing draft, sources, confidence, route rationale, and Approve/Reject/Edit/Regenerate/Escalate buttons.
- Persist reviewer decisions to Postgres; update ticket status.

**Data flow**: `rag_retrieve → draft_answer → route_decision → confidence_recheck → (loop to rag_retrieve | proceed to hitl_gate)`

**Evaluation**:
- Groundedness score distribution before/after the loop (should shift upward).
- Reviewer edit rate (proxy for draft quality) — target trending down over iterations.
- Latency budget per ticket (retrieval loop should add ≤1 extra round-trip on average).

**Success criteria**: loop reduces "escalate due to low confidence" false-escalations by a measurable margin on the golden set without increasing fabricated-citation rate.

### Phase 3 — Memory, Multi-turn, and Category Specialization (1 week)
**Goals**: handle `conversation_history` properly; specialize agents per category.

**Key components**:
- LangChain memory (conversation buffer per `customer_id`/`ticket_id`) so follow-up tickets/messages retain context.
- Category-specialized sub-agents/tools (`triage_agent.py`, `rag_agent.py`) — e.g., a dedicated refund-rule tool, an account-access tool that checks for required identifiers.
- ReAct-style reasoning trace captured for audit (why the agent chose a tool/route), stored alongside the audit log.

**Success criteria**: multi-turn tickets correctly incorporate prior turns in the draft; category-specific rule violations (e.g., missing account ID) correctly trigger Ask-for-Info.

### Phase 4 — Evaluation Rigor, Monitoring, Hardening (1 week)
**Goals**: production-readiness.

**Key components**:
- Arize (or LangSmith/Phoenix) integration for trace-level evaluation: groundedness, answer relevance, route correctness, drift over time.
- Regression test suite (`test_hitl_flow.py` and friends) run in CI on every change to prompts/KB/routing rules.
- Structured logging + dashboards (ticket volume by route, escalation rate, average confidence, reviewer approval/edit/reject rates).
- Security review: PII redaction before any data leaves the pipeline to an external eval/monitoring service; secrets via `.env` (never committed — `.env.example` only).

**Success criteria**: CI gate blocking merge if route accuracy or groundedness regresses beyond a defined threshold; monitoring dashboard live.

### Phase 5 (Optional / Stretch) — Scale & Productionization
- Swap FAISS → managed vector store (Azure AI Search/Pinecone) for larger KBs.
- Queue-based async processing (e.g., Celery/RQ or a message broker) for ticket volume spikes.
- Role-based auth for reviewers (admin vs L1 support) via SSO.
- A/B testing of prompt variants through the eval harness before promoting to default.

---

## 4. Technical Design Details

### 4.1 LangChain / LangGraph Patterns

- **StateGraph over Chains**: Because routing has real branching + loops (retrieval refinement, HITL edit → regenerate), LangGraph's `StateGraph` is the right primitive — plain LangChain sequential chains can't express the conditional loop-backs.
- **Conditional edges** for the four-way route decision:
```python
graph.add_conditional_edges(
    "route_decision",
    lambda state: state["route_decision"],
    {
        "AUTO_RESOLVE": "confidence_recheck",
        "ESCALATE": "hitl_gate",
        "REFUSE": "hitl_gate",
        "ASK_INFO": "hitl_gate",
    },
)
```
- **Refinement loop**:
```python
graph.add_conditional_edges(
    "confidence_recheck",
    lambda state: "retry" if (state["groundedness_score"] < THRESHOLD
                               and state["retrieval_attempts"] < MAX_ATTEMPTS)
                  else "proceed",
    {"retry": "rag_retrieve", "proceed": "hitl_gate"},
)
```
- **Tools as deterministic guards**: refund-window check, repeated-request check, and abuse detection should be implemented as plain Python "tools" the graph calls, not left purely to LLM judgment — this keeps the safety-critical logic auditable and testable.
- **Retriever as a LangChain `Retriever`** wrapped in a node function so it's swappable (FAISS → Chroma → managed store) without touching graph logic.
- **Memory**: `ConversationBufferMemory` (or a custom store keyed by `customer_id`) injected into the draft-answer prompt for multi-turn tickets.

### 4.2 Prompt Templates (representative)

**Sentiment & Category Classification** (structured output)
```
System: Classify the support ticket. Return JSON only:
{"sentiment": "positive|neutral|negative|abusive",
 "category": "refund_request|subscription_cancellation|login_access|troubleshooting|abusive_content|other",
 "requires_more_info": true|false,
 "missing_fields": ["..."]}

Ticket: {subject} / {message}
```

**Grounded Draft Answer**
```
System: You are a support draft-writer. You may ONLY state policy facts that
appear in the CONTEXT below, with a source citation. If the context does not
answer the customer's question, say plainly that the relevant policy could
not be verified and recommend escalation. Never invent policy details.

Context:
{retrieved_chunks}

Customer message:
{ticket_message}

Write a draft reply (not sent to customer) citing sources like [source: refund_policy.md].
```

**Groundedness Check** (LLM-as-judge, or embedding-similarity fallback)
```
System: Given the DRAFT and the CONTEXT, score 0-1 how well every factual
claim in DRAFT is supported by CONTEXT. Flag any unsupported claim.
Return JSON: {"score": float, "unsupported_claims": ["..."]}
```

### 4.3 Safety Considerations
- **Hard block on auto-send**: no node/tool in the graph has network access to email/SMS/customer-facing channels — this should be enforced architecturally (no such tool registered), not just by prompt instruction.
- **Refusal path is scripted, not generative**: abusive-content and refund-abuse refusals use a fixed template pulled from `abusive_content_policy.md`, not an LLM-generated response, to avoid tone drift or leaking internal reasoning.
- **No-policy-found is a first-class outcome**: explicitly modeled in `GraphState.route_decision`, tested in the golden dataset, not just handled implicitly by low confidence.
- **Citation enforcement**: a post-generation check verifies every policy claim in the draft has a matching `retrieved_sources` entry; if not, force `ESCALATE`.

### 4.4 Data Handling, Privacy, Security
- Synthetic data only for dev/eval — no real customer PII in the repo.
- `.env` for API keys; `.env.example` checked in with placeholders only.
- If integrating a real ticket system later: redact PII (names, emails, payment info) before sending ticket text to any third-party eval/monitoring tool (Arize, etc.).
- Audit log is append-only (no deletes/edits) — supports compliance review of every AI decision.
- Access control on the HITL reviewer endpoints (auth required to approve/reject).

### 4.5 Deployment Stack

| Environment | Stack |
|---|---|
| Dev | Local FastAPI + FAISS (in-memory/on-disk) + SQLite, run via `uvicorn` / docker-compose |
| CI | GitHub Actions: lint, unit tests, golden-dataset regression eval on PR |
| Prod | FastAPI (containerized) + Postgres + managed vector store (Chroma server or Azure AI Search) + reviewer UI (Next.js) behind auth; LangSmith/Arize for tracing |
| Monitoring | Dashboards: route distribution, escalation rate, avg confidence/groundedness, reviewer approval/edit/reject rates, latency p50/p95 |

---

## 5. Milestones, Timeline, Resource Estimate

| Milestone | Duration | Owner(s) | Deliverable |
|---|---|---|---|
| Phase 0: Setup | 0.5 wk | 1 eng | Repo, synthetic tickets, KB |
| Phase 1: MVP flow | 1.5–2 wk | 1–2 eng | End-to-end draft generation + basic HITL stub |
| Phase 2: Confidence loop + UI | 1.5 wk | 1 eng + 0.5 frontend | Retrieval refinement, reviewer UI |
| Phase 3: Memory & specialization | 1 wk | 1 eng | Multi-turn support, category tools |
| Phase 4: Eval & hardening | 1 wk | 1 eng + eval support | CI gates, monitoring, security review |
| Phase 5 (optional): Scale | 1–2 wk | 1–2 eng | Managed vector store, async queue, RBAC |

**Total core build (Phases 0–4): ~5.5–6.5 weeks** for a small team (1–2 engineers), consistent with a capstone/participant-ready project scope.

---

## 6. Final Submission Checklist (from PDF, retained)
- [ ] Synthetic ticket queue included
- [ ] Knowledge base files included
- [ ] LangGraph flow implemented
- [ ] RAG retrieval working
- [ ] Route decision working
- [ ] HITL approval gate implemented
- [ ] Audit logging implemented
- [ ] Evaluation report against golden dataset

---

## 7. Suggested Final-Document Outline (PDF-ready)

1. Executive Summary
2. Problem Statement & Safety Principles
3. System Architecture (diagram + data model)
4. Phased Implementation Plan (this doc, Section 3)
5. Technical Design (LangGraph patterns, prompts, safety)
6. Evaluation Plan & Results
7. Deployment & Monitoring
8. Milestones & Timeline
9. Appendix: API contracts, config schemas, sample tickets/KB entries

*This markdown file can be converted directly to a Word document or PDF for participant/stakeholder distribution — just say the word if you'd like it exported that way.*
