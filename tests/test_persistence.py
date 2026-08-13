from src.persistence.db import ReviewStore


def _store(tmp_path):
    return ReviewStore(tmp_path / "test.db")


def test_insert_and_list_pending(tmp_path):
    store = _store(tmp_path)
    review_id = store.insert_review(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="subject",
        message="message",
        draft_reply="draft",
        route_decision="AUTO_RESOLVE",
        route_reason="policy_grounded_response",
        confidence_score=0.5,
        llm_groundedness_score=0.9,
        retrieved_sources=["refund_policy.md"],
        reviewer_action=None,
        status="PENDING_REVIEW",
    )
    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == review_id
    assert pending[0]["retrieved_sources"] == ["refund_policy.md"]
    assert pending[0]["status"] == "PENDING_REVIEW"


def test_update_review_marks_approved_and_leaves_pending_list_empty(tmp_path):
    store = _store(tmp_path)
    review_id = store.insert_review(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="subject",
        message="message",
        draft_reply="draft",
        route_decision="AUTO_RESOLVE",
        route_reason="policy_grounded_response",
        confidence_score=0.5,
        llm_groundedness_score=0.9,
        retrieved_sources=[],
        reviewer_action=None,
        status="PENDING_REVIEW",
    )
    store.update_review(review_id, reviewer_action="APPROVED", status="APPROVED", reviewer_comments="looks good")

    assert store.list_pending() == []
    record = store.get(review_id)
    assert record["reviewer_action"] == "APPROVED"
    assert record["status"] == "APPROVED"
    assert record["reviewer_comments"] == "looks good"


def test_edit_action_persists_edited_reply(tmp_path):
    store = _store(tmp_path)
    review_id = store.insert_review(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="subject",
        message="message",
        draft_reply="original draft",
        route_decision="AUTO_RESOLVE",
        route_reason="policy_grounded_response",
        confidence_score=0.5,
        llm_groundedness_score=0.9,
        retrieved_sources=[],
        reviewer_action=None,
        status="PENDING_REVIEW",
    )
    store.update_review(review_id, reviewer_action="EDITED", status="APPROVED", edited_reply="fixed draft")

    record = store.get(review_id)
    assert record["edited_reply"] == "fixed draft"
    assert record["draft_reply"] == "original draft"


def test_count_for_ticket_tracks_rows_across_regenerations(tmp_path):
    store = _store(tmp_path)
    assert store.count_for_ticket("TCK-TEST") == 0

    store.insert_review(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="s",
        message="m",
        draft_reply="d1",
        route_decision="AUTO_RESOLVE",
        route_reason="policy_grounded_response",
        confidence_score=0.5,
        llm_groundedness_score=0.9,
        retrieved_sources=[],
        reviewer_action=None,
        status="PENDING_REVIEW",
        regenerate_count=0,
    )
    assert store.count_for_ticket("TCK-TEST") == 1

    store.insert_review(
        ticket_id="TCK-TEST",
        customer_id="CUST-TEST",
        subject="s",
        message="m",
        draft_reply="d2",
        route_decision="AUTO_RESOLVE",
        route_reason="policy_grounded_response",
        confidence_score=0.5,
        llm_groundedness_score=0.9,
        retrieved_sources=[],
        reviewer_action=None,
        status="PENDING_REVIEW",
        regenerate_count=1,
    )
    assert store.count_for_ticket("TCK-TEST") == 2
