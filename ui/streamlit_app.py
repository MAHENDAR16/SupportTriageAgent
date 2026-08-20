from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.config.settings import get_settings
from src.graph.build_graph import build_default_deps, build_graph
from src.hitl import approval_queue, reviewer_actions

st.set_page_config(page_title="Support Triage Reviewer", layout="wide")


@st.cache_resource
def _get_deps_and_graph():
    settings = get_settings()
    deps = build_default_deps(auto_approve=False, interactive=False, settings=settings)
    graph = build_graph(deps)
    tickets_by_id = approval_queue.load_tickets_by_id(settings)
    return deps, graph, tickets_by_id


deps, graph, tickets_by_id = _get_deps_and_graph()


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"


st.title("Support Triage — Reviewer Queue")
st.caption(
    "Every draft below is unsent. Nothing reaches a customer until you Approve, Edit, "
    "Reject, or Escalate it here."
)

with st.sidebar:
    st.header("Process a ticket")
    ticket_id = st.selectbox("Ticket", sorted(tickets_by_id.keys()))
    if st.button("Run agent", type="primary"):
        with st.spinner(f"Running the triage agent on {ticket_id}..."):
            reviewer_actions.process_ticket(ticket_id, deps, graph, tickets_by_id)
        st.success(f"{ticket_id} processed — see the queue below.")
        st.rerun()

    st.divider()
    st.metric("Pending review", len(approval_queue.list_pending(deps)))

tab_queue, tab_history = st.tabs(["Queue", "History"])

with tab_queue:
    pending = approval_queue.list_pending(deps)
    if not pending:
        st.info("No tickets waiting for review. Process one from the sidebar.")

    for record in pending:
        with st.container(border=True):
            st.subheader(f"{record['ticket_id']} — {record['subject']}")
            left, right = st.columns([2, 1])

            with left:
                st.write(f"**Customer message:** {record['message']}")
                st.write(f"**Route:** `{record['route_decision']}` — {record['route_reason']}")
                st.write(f"**Sources:** {', '.join(record['retrieved_sources']) or 'none'}")
                st.write(
                    f"**Retrieval groundedness:** {_fmt(record['confidence_score'])}"
                    f"  |  **LLM-judge groundedness:** {_fmt(record['llm_groundedness_score'])}"
                )
                if record["regenerate_count"]:
                    st.caption(f"Regenerated {record['regenerate_count']} time(s)")
                st.text_area(
                    "Draft reply",
                    record["draft_reply"],
                    height=180,
                    key=f"draft_{record['id']}",
                    disabled=True,
                )

            with right:
                comments = st.text_input("Comments", key=f"comments_{record['id']}")
                if st.button("Approve", key=f"approve_{record['id']}", type="primary"):
                    reviewer_actions.approve_review(record["id"], deps, comments=comments)
                    st.rerun()
                if st.button("Reject", key=f"reject_{record['id']}"):
                    reviewer_actions.reject_review(record["id"], deps, comments=comments)
                    st.rerun()
                if st.button("Escalate", key=f"escalate_{record['id']}"):
                    reviewer_actions.escalate_review(record["id"], deps, comments=comments)
                    st.rerun()
                if st.button("Regenerate", key=f"regen_{record['id']}"):
                    with st.spinner("Regenerating draft..."):
                        reviewer_actions.regenerate(record["id"], deps, graph, tickets_by_id)
                    st.rerun()

            with st.expander("Edit reply"):
                edited = st.text_area(
                    "Edited reply", record["draft_reply"], key=f"edit_{record['id']}", height=150
                )
                if st.button("Save edit & approve", key=f"save_edit_{record['id']}"):
                    reviewer_actions.edit_review(record["id"], edited, deps, comments=comments)
                    st.rerun()

with tab_history:
    history = approval_queue.list_all(deps)
    if not history:
        st.info("No review history yet.")
    else:
        table_rows = [
            {
                "id": r["id"],
                "ticket_id": r["ticket_id"],
                "route_decision": r["route_decision"],
                "reviewer_action": r["reviewer_action"],
                "status": r["status"],
                "regenerate_count": r["regenerate_count"],
                "created_at": r["created_at"],
            }
            for r in history
        ]
        st.dataframe(table_rows, use_container_width=True)

        resolved = [r for r in history if r["reviewer_action"]]
        if resolved:
            edit_rate = sum(1 for r in resolved if r["reviewer_action"] == "EDITED") / len(resolved)
            st.metric(
                "Reviewer edit rate",
                f"{edit_rate:.1%}",
                help="Share of resolved reviews where the reviewer edited the draft "
                "rather than approving/rejecting/escalating it as-is.",
            )
