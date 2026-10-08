import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# use a throw-away DB for tests (must be set before importing config)
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

import database as db  # noqa: E402
import tools  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def seeded():
    db.seed_if_empty()
    yield


def test_seed_is_idempotent():
    db.seed_if_empty()
    assert len(db.list_tickets()) == 5


def test_customer_and_invoices():
    assert db.get_customer(1)["name"] == "Aarav Mehta"
    assert db.get_customer(999) is None
    assert any(i["status"] == "overdue" for i in db.get_invoices(4))


def test_tools_return_json():
    assert json.loads(tools.get_customer_profile.invoke({"customer_id": 2}))["plan"] == "Starter"
    assert len(json.loads(tools.get_billing_info.invoke({"customer_id": 1}))) == 3
    assert "error" in json.loads(tools.get_customer_profile.invoke({"customer_id": 999}))
    assert len(json.loads(tools.get_ticket_history.invoke({"customer_id": 1}))) == 2


def test_tool_registry():
    assert set(tools.TOOL_MAP) == {"get_customer_profile", "get_billing_info", "get_ticket_history"}


def test_api_basic_routes():
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert len(client.get("/tickets").json()) == 5
        r = client.get("/tickets/1").json()
        assert r["customer"]["email"] == "aarav@example.com"
        assert client.get("/tickets/999").status_code == 404


def test_ticket_1_scenario_has_a_real_duplicate_charge():
    october = [i for i in db.get_invoices(1) if i["due_date"].startswith("2026-10")]
    assert len(october) == 2 and all(i["amount"] == 49.0 for i in october)
