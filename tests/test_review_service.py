from src.agents.classifier import ClassificationResult
from src.agents.groundedness import GroundednessJudgment
from src.audit.logger import AuditLogger
from src.config.settings import get_settings
from src.graph import build_graph as build_graph_module
from src.graph.deps import GraphDeps
from src.graph.nodes import confidence_recheck as confidence_recheck_module
from src.graph.nodes import draft_answer as draft_answer_module
from src.graph.nodes import sentiment_policy_check as sentiment_policy_check_module
from src.persistence.db import ReviewStore
from src.rag.retriever import build_retriever
from src.services import review_service

settings = get_settings()


def _queue_mode_deps(tmp_path) -> GraphDeps:
    return GraphDeps(
        settings=settings,
        llm=None,  # never actually invoked -- classify/draft/judge are monkeypatched below
        retriever=build_retriever(settings),
        audit_logger=AuditLogger(tmp_path / "audit.jsonl"),
        auto_approve=False,
        interactive=False,
        review_store=ReviewStore(tmp_path / "reviews.db"),
    )


def _stub_llm_calls(monkeypatch):
    monkeypatch.setattr(
        sentiment_policy_check_module,
        "classify_ticket",
        lambda ticket, llm, settings: ClassificationResult(
            sentiment="neutral", category="refund_request", requires_more_info=False, missing_fields=[]
        ),
    )
    monkeypatch.setattr(
        draft_answer_module,
        "generate_draft",
        lambda ticket, chunks, llm: "Your refund is within policy. [source: refund_policy.md]",
    )
    monkeypatch.setattr(
        confidence_recheck_module,
        "judge_groundedness",
        lambda draft, chunks, llm: GroundednessJudgment(score=0.95, unsupported_claims=[]),
    )


def test_process_ticket_lands_pending_review_without_blocking(tmp_path, monkeypatch):
    _stub_llm_calls(monkeypatch)
    deps = _queue_mode_deps(tmp_path)
    graph = build_graph_module.build_graph(deps)
    tickets_by_id = review_service.load_tickets_by_id(settings)

    result = review_service.process_ticket("TCK-1001", deps, graph, tickets_by_id)

    assert result["route_decision"] == "AUTO_RESOLVE"
    assert result["reviewer_action"] is None
    assert result["review_id"] is not None

    pending = review_service.list_pending(deps)
    assert len(pending) == 1
    assert pending[0]["ticket_id"] == "TCK-1001"
    assert pending[0]["status"] == "PENDING_REVIEW"
    assert pending[0]["llm_groundedness_score"] == 0.95


def test_edit_action_resolves_the_queue_item(tmp_path, monkeypatch):
    _stub_llm_calls(monkeypatch)
    deps = _queue_mode_deps(tmp_path)
    graph = build_graph_module.build_graph(deps)
    tickets_by_id = review_service.load_tickets_by_id(settings)

    review_service.process_ticket("TCK-1001", deps, graph, tickets_by_id)
    review_id = review_service.list_pending(deps)[0]["id"]

    review_service.submit_review(
        review_id, "EDITED", deps, comments="tightened wording", edited_reply="Final edited reply."
    )

    assert review_service.list_pending(deps) == []
    record = deps.review_store.get(review_id)
    assert record["status"] == "EDITED"
    assert record["edited_reply"] == "Final edited reply."
    assert record["draft_reply"] == "Your refund is within policy. [source: refund_policy.md]"


def test_regenerate_supersedes_old_row_and_creates_a_new_pending_one(tmp_path, monkeypatch):
    _stub_llm_calls(monkeypatch)
    deps = _queue_mode_deps(tmp_path)
    graph = build_graph_module.build_graph(deps)
    tickets_by_id = review_service.load_tickets_by_id(settings)

    review_service.process_ticket("TCK-1001", deps, graph, tickets_by_id)
    original_review_id = review_service.list_pending(deps)[0]["id"]

    review_service.regenerate(original_review_id, deps, graph, tickets_by_id)

    original = deps.review_store.get(original_review_id)
    assert original["status"] == "SUPERSEDED"
    assert original["reviewer_action"] == "REGENERATED"

    pending = review_service.list_pending(deps)
    assert len(pending) == 1
    assert pending[0]["id"] != original_review_id
    assert pending[0]["ticket_id"] == "TCK-1001"
    assert pending[0]["regenerate_count"] == 1


def test_abusive_ticket_bypasses_llm_draft_and_confidence_recheck(tmp_path, monkeypatch):
    """The classifier still runs (sentiment/category detection isn't
    abuse-conditional), but draft generation and confidence_recheck are both
    skipped for the abuse path -- deterministic abuse detection short-
    circuits to the scripted refusal template and route_decision routes
    straight to hitl_gate, bypassing confidence_recheck entirely."""
    _stub_llm_calls(monkeypatch)
    deps = _queue_mode_deps(tmp_path)
    graph = build_graph_module.build_graph(deps)
    tickets_by_id = review_service.load_tickets_by_id(settings)

    result = review_service.process_ticket("TCK-1009", deps, graph, tickets_by_id)

    assert result["route_decision"] == "REFUSE"
    assert result["draft_reply"] == settings.refusal_templates["abusive"]
    assert "llm_groundedness_score" not in result  # confidence_recheck never ran
    pending = review_service.list_pending(deps)
    assert len(pending) == 1
    assert pending[0]["route_decision"] == "REFUSE"
