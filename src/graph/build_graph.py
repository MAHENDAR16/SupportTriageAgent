from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.agents.llm_client import build_llm
from src.config.settings import Settings, get_settings
from src.graph.deps import GraphDeps
from src.logging.audit_logger import AuditLogger
from src.memory.conversation_memory import ConversationMemory
from src.memory.customer_thread_store import CustomerThreadStore
from src.observability.tracing import setup_tracing
from src.graph.nodes.audit_log import make_audit_log_node
from src.graph.nodes.confidence_recheck import make_confidence_recheck_node
from src.graph.nodes.draft_answer import make_draft_answer_node
from src.graph.nodes.hitl_gate import make_hitl_gate_node
from src.graph.nodes.ingest import make_ingest_node
from src.graph.nodes.rag_retrieve import make_rag_retrieve_node
from src.graph.nodes.route_decision import make_route_decision_node
from src.graph.nodes.sentiment_policy_check import make_sentiment_policy_check_node
from src.graph.state import GraphState
from src.persistence.db import ReviewStore
from src.rag.retriever import build_retriever


# Assembles the default GraphDeps bundle: LLM client, retriever, audit
# logger, memory/thread stores, and the reviewer DB. Also enables Arize
# LLM tracing (once per process) when ARIZE_API_KEY/ARIZE_SPACE_ID are set.
def build_default_deps(
    auto_approve: bool = False,
    interactive: bool = True,
    settings: Settings | None = None,
) -> GraphDeps:
    settings = settings or get_settings()
    setup_tracing(settings)
    return GraphDeps(
        settings=settings,
        llm=build_llm(settings),
        retriever=build_retriever(settings),
        audit_logger=AuditLogger(settings.audit_log_path),
        conversation_memory=ConversationMemory(max_conversations=100),
        thread_store=CustomerThreadStore(settings.thread_store_path),
        auto_approve=auto_approve,
        interactive=interactive,
        review_store=ReviewStore(settings.reviewer_db_path),
    )


# Conditional-edge selector after the route node: reads route_decision to
# send AUTO_RESOLVE through confidence_recheck and everything else to hitl_gate.
def _route_branch(state: GraphState) -> str:
    """AUTO_RESOLVE gets a second, stricter LLM-as-judge pass before it's
    finalized; the other three routes are already "safe" outcomes (escalate/
    refuse/ask-info) that don't need it."""
    return state["route_decision"]


# Conditional-edge selector after confidence_recheck: proceeds to hitl_gate
# once passed or force-escalated, otherwise loops back to rag_retrieve to retry.
def _confidence_recheck_branch(state: GraphState) -> str:
    if state["route_decision"] != "AUTO_RESOLVE":
        # confidence_recheck itself forced an override to ESCALATE because
        # retries were exhausted -- proceed to hitl_gate with that decision.
        return "proceed"
    if state.get("llm_groundedness_passed", True):
        return "proceed"
    return "retry"


# Wires all pipeline nodes and conditional edges into a compiled LangGraph
# StateGraph, implementing the full ingest -> ... -> audit_log flow.
def build_graph(deps: GraphDeps):
    """Phase 2: adds the confidence-recheck refinement loop (§3 Phase 2).
    route_decision -> confidence_recheck only for AUTO_RESOLVE; a failing
    judge score with retries remaining loops back to rag_retrieve with a
    reformulated query, otherwise confidence_recheck forces ESCALATE."""
    graph = StateGraph(GraphState)

    graph.add_node("ingest", make_ingest_node(deps))
    graph.add_node("sentiment_policy_check", make_sentiment_policy_check_node(deps))
    graph.add_node("rag_retrieve", make_rag_retrieve_node(deps))
    graph.add_node("draft_answer", make_draft_answer_node(deps))
    # Node id is "route" (not "route_decision") -- LangGraph forbids a node
    # name identical to a GraphState key, and "route_decision" is the state
    # field this node writes. The audit log entry it emits is still tagged
    # "route_decision" for readability.
    graph.add_node("route", make_route_decision_node(deps))
    graph.add_node("confidence_recheck", make_confidence_recheck_node(deps))
    graph.add_node("hitl_gate", make_hitl_gate_node(deps))
    graph.add_node("audit_log", make_audit_log_node(deps))

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "sentiment_policy_check")
    graph.add_edge("sentiment_policy_check", "rag_retrieve")
    graph.add_edge("rag_retrieve", "draft_answer")
    graph.add_edge("draft_answer", "route")
    graph.add_conditional_edges(
        "route",
        _route_branch,
        {
            "AUTO_RESOLVE": "confidence_recheck",
            "ESCALATE": "hitl_gate",
            "REFUSE": "hitl_gate",
            "ASK_INFO": "hitl_gate",
        },
    )
    graph.add_conditional_edges(
        "confidence_recheck",
        _confidence_recheck_branch,
        {"retry": "rag_retrieve", "proceed": "hitl_gate"},
    )
    graph.add_edge("hitl_gate", "audit_log")
    graph.add_edge("audit_log", END)

    return graph.compile()
