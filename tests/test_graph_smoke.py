from src.config.settings import get_settings
from src.graph.build_graph import build_default_deps, build_graph
from src.main import load_tickets

settings = get_settings()
tickets = {t.ticket_id: t for t in load_tickets(settings)}
deps = build_default_deps(auto_approve=True, settings=settings)
graph = build_graph(deps)


def _run(ticket_id: str) -> dict:
    return graph.invoke({"ticket": tickets[ticket_id]})


def test_abusive_ticket_is_refused_without_calling_llm_for_the_reply():
    result = _run("TCK-1009")
    assert result["route_decision"] == "REFUSE"
    assert result["draft_reply"] == settings.refusal_templates["abusive"]


def test_refund_abuse_language_is_refused():
    result = _run("TCK-1010")
    assert result["route_decision"] == "REFUSE"
    assert result["draft_reply"] == settings.refusal_templates["refund_abuse"]


def test_grounded_refund_request_auto_resolves_with_citation():
    result = _run("TCK-1001")
    assert result["route_decision"] == "AUTO_RESOLVE"
    assert "[source:" in result["draft_reply"]
    assert not result["fabricated_citations"]


def test_out_of_scope_question_escalates_with_no_fabricated_policy():
    result = _run("TCK-1017")
    assert result["route_decision"] == "ESCALATE"
    assert not result["fabricated_citations"]


def test_every_ticket_gets_a_reviewer_action_and_never_skips_hitl():
    for ticket_id in tickets:
        result = _run(ticket_id)
        assert result["reviewer_action"] == "APPROVED"
        assert result["route_decision"] in {"AUTO_RESOLVE", "ESCALATE", "REFUSE", "ASK_INFO"}
