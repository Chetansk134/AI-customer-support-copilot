"""LangChain tools the LLM can call: mock CRM + billing lookups (Infrastructure layer)."""
import json

from langchain_core.tools import tool

import database as db


@tool
def get_customer_profile(customer_id: int) -> str:
    """Look up a customer's CRM profile: name, email, plan and account status."""
    cust = db.get_customer(customer_id)
    return json.dumps(cust) if cust else json.dumps({"error": f"customer {customer_id} not found"})


@tool
def get_billing_info(customer_id: int) -> str:
    """Look up a customer's recent invoices: invoice number, amount, status (paid/refunded/overdue) and due date."""
    return json.dumps(db.get_invoices(customer_id))


@tool
def get_ticket_history(customer_id: int) -> str:
    """Look up a customer's previous support tickets (subject and status)."""
    rows = db.get_customer_tickets(customer_id)
    return json.dumps([{"id": r["id"], "subject": r["subject"], "status": r["status"]} for r in rows])


TOOLS = [get_customer_profile, get_billing_info, get_ticket_history]
TOOL_MAP = {t.name: t for t in TOOLS}
