"""Streamlit dashboard (Presentation layer): pick a ticket -> generate draft -> edit -> approve."""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Support Copilot", page_icon="🎧", layout="wide")


def api_get(path: str):
    r = requests.get(f"{API_URL}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json=None, timeout: int = 120):
    r = requests.post(f"{API_URL}{path}", json=json, timeout=timeout)
    r.raise_for_status()
    return r.json()


st.title("🎧 Customer Support Copilot")
st.caption("RAG + customer memory + tool calling → a ready-to-review reply in one click")

try:
    tickets = api_get("/tickets")
except Exception as exc:  # noqa: BLE001
    st.error(f"Cannot reach the API at {API_URL}: {exc}")
    st.stop()

# ---------------- Sidebar: ticket list ----------------
with st.sidebar:
    st.header("Tickets")
    status_filter = st.radio("Show", ["open", "resolved", "all"], horizontal=True)
    shown = [t for t in tickets if status_filter == "all" or t["status"] == status_filter]
    if not shown:
        st.info("No tickets in this view.")
        st.stop()
    labels = {t["id"]: f"#{t['id']} · {t['subject']}" for t in shown}
    ticket_id = st.selectbox("Select a ticket", list(labels), format_func=labels.get)

# ---------------- Main: ticket + customer ----------------
detail = api_get(f"/tickets/{ticket_id}")
ticket, customer = detail["ticket"], detail["customer"]

left, right = st.columns([2, 1])
with left:
    st.subheader(f"#{ticket['id']} · {ticket['subject']}")
    st.write(ticket["body"])
    st.caption(f"Status: {ticket['status']}")
with right:
    st.markdown("**Customer**")
    st.write(f"{customer['name']} · {customer['email']}")
    st.write(f"Plan: **{customer['plan']}** · Account: **{customer['status']}**")

st.divider()

# ---------------- Draft generation ----------------
draft_key, ver_key = f"draft_{ticket_id}", f"ver_{ticket_id}"

if st.button("✨ Generate reply", type="primary", disabled=ticket["status"] == "resolved"):
    with st.spinner("Gathering memory, knowledge base and billing data…"):
        try:
            st.session_state[draft_key] = api_post(f"/tickets/{ticket_id}/draft")
            st.session_state[ver_key] = st.session_state.get(ver_key, 0) + 1
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not generate a draft: {exc}")

result = st.session_state.get(draft_key)
if result:
    st.subheader("Draft reply (editable)")
    final_text = st.text_area(
        "Edit before sending",
        value=result["draft"],
        height=260,
        key=f"edit_{ticket_id}_{st.session_state.get(ver_key, 0)}",
        label_visibility="collapsed",
    )

    if st.button("✅ Approve & send"):
        try:
            api_post(f"/tickets/{ticket_id}/approve", json={"final_reply": final_text})
            st.session_state.pop(draft_key, None)
            st.success("Reply approved. Ticket resolved and the customer's memory was updated.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not approve: {exc}")

    ctx = result["context"]
    st.subheader("Context used")
    with st.expander(f"🧠 Customer memory ({len(ctx['memories'])})"):
        for m in ctx["memories"] or ["No stored memories yet for this customer."]:
            st.write(f"- {m}")
    with st.expander(f"📚 Knowledge base ({len(ctx['kb_snippets'])})"):
        for s in ctx["kb_snippets"]:
            st.markdown(f"**{s['source']}**")
            st.write(s["text"])
    with st.expander(f"🛠️ Tool calls ({len(ctx['tool_results'])})"):
        for t in ctx["tool_results"]:
            st.markdown(f"**{t['tool']}** `{t['args']}`")
            st.json(t["output"])
