"""Smoke-tests the Streamlit dashboard with a fake API (no server, LLM or network needed)."""
import os
import sys
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")

TICKETS = [
    {"id": 1, "customer_id": 1, "subject": "Charged twice", "body": "Two charges this month", "status": "open"},
    {"id": 2, "customer_id": 2, "subject": "Cannot log in", "body": "Account locked", "status": "resolved"},
]
DETAIL = {
    "ticket": TICKETS[0],
    "customer": {"id": 1, "name": "Aarav Mehta", "email": "aarav@example.com", "plan": "Pro", "status": "active"},
}
DRAFT = {
    "ticket_id": 1,
    "draft": "Hi Aarav, we refunded the duplicate charge. Support Team",
    "context": {
        "memories": ["Prefers email"],
        "kb_snippets": [{"source": "refund-policy.md", "text": "Duplicates are refunded."}],
        "tool_results": [{"tool": "get_billing_info", "args": {"customer_id": 1}, "output": []}],
    },
}


def _resp(data):
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


def fake_get(url, **kw):
    return _resp(TICKETS if url.endswith("/tickets") else DETAIL)


def fake_post(url, **kw):
    return _resp(DRAFT if url.endswith("/draft") else {"status": "resolved"})


def test_dashboard_generate_and_approve():
    with patch("requests.get", fake_get), patch("requests.post", fake_post):
        at = AppTest.from_file(APP, default_timeout=30).run()
        assert not at.exception
        assert any("Aarav Mehta" in m.value for m in at.markdown)

        at.button[0].click().run()  # Generate reply
        assert not at.exception
        assert at.text_area[0].value.startswith("Hi Aarav")

        at.button[1].click().run()  # Approve & send
        assert not at.exception
        assert any("approved" in s.value.lower() for s in at.success)


def test_dashboard_shows_error_when_api_down():
    def boom(*a, **k):
        raise ConnectionError("down")

    with patch("requests.get", boom):
        at = AppTest.from_file(APP, default_timeout=30).run()
        assert any("Cannot reach the API" in e.value for e in at.error)
