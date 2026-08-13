from src.agents.groundedness import GroundednessJudgment
from src.audit.logger import AuditLogger
from src.config.settings import get_settings
from src.graph.deps import GraphDeps
from src.graph.nodes import confidence_recheck as confidence_recheck_module
from src.models.ticket import Ticket

settings = get_settings()


def _deps(tmp_path) -> GraphDeps:
    return GraphDeps(
        settings=settings,
        llm=None,
        retriever=None,
        audit_logger=AuditLogger(tmp_path / "audit.jsonl"),
        auto_approve=True,
    )


def _state(**overrides) -> dict:
    base = dict(
        ticket=Ticket(ticket_id="TCK-TEST", customer_id="CUST-TEST", subject="s", message="m"),
        draft_reply="draft",
        retrieved_chunks=[{"source": "refund_policy.md", "text": "...", "score": 0.6}],
        retrieval_attempts=1,
        route_decision="AUTO_RESOLVE",
    )
    base.update(overrides)
    return base


def test_passing_judgment_proceeds_without_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(
        confidence_recheck_module,
        "judge_groundedness",
        lambda draft, chunks, llm: GroundednessJudgment(score=0.95, unsupported_claims=[]),
    )
    node = confidence_recheck_module.make_confidence_recheck_node(_deps(tmp_path))
    result = node(_state())

    assert result["llm_groundedness_passed"] is True
    assert "route_decision" not in result  # unchanged, still AUTO_RESOLVE from before this node ran


def test_failing_judgment_with_retries_remaining_sets_retry_hint(tmp_path, monkeypatch):
    monkeypatch.setattr(
        confidence_recheck_module,
        "judge_groundedness",
        lambda draft, chunks, llm: GroundednessJudgment(score=0.2, unsupported_claims=["annual plan discount"]),
    )
    node = confidence_recheck_module.make_confidence_recheck_node(_deps(tmp_path))
    result = node(_state(retrieval_attempts=1))  # max_retrieval_attempts is 2, so 1 < 2 -> retry

    assert result["llm_groundedness_passed"] is False
    assert result["query_reformulation_hint"] == "annual plan discount"
    assert "route_decision" not in result  # not overridden -- edge lambda will route to rag_retrieve


def test_failing_judgment_after_max_attempts_forces_escalate(tmp_path, monkeypatch):
    monkeypatch.setattr(
        confidence_recheck_module,
        "judge_groundedness",
        lambda draft, chunks, llm: GroundednessJudgment(score=0.1, unsupported_claims=["made up policy"]),
    )
    node = confidence_recheck_module.make_confidence_recheck_node(_deps(tmp_path))
    result = node(_state(retrieval_attempts=settings.max_retrieval_attempts))  # attempts exhausted

    assert result["llm_groundedness_passed"] is False
    assert result["route_decision"] == "ESCALATE"
    assert result["route_reason"] == "low_confidence_after_retries"
