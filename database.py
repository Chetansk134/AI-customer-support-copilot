"""SQLite access layer + seed data (mock CRM / billing / tickets / drafts)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY, name TEXT, email TEXT, plan TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, invoice_no TEXT,
    amount REAL, status TEXT, due_date TEXT
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, subject TEXT, body TEXT,
    status TEXT DEFAULT 'open', created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, content TEXT,
    approved INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CUSTOMERS = [
    (1, "Aarav Mehta", "aarav@example.com", "Pro", "active"),
    (2, "Diya Rao", "diya@example.com", "Starter", "active"),
    (3, "Kabir Shah", "kabir@example.com", "Enterprise", "active"),
    (4, "Meera Nair", "meera@example.com", "Pro", "past_due"),
]
BILLING = [
    (1, "INV-1001", 49.0, "paid", "2026-09-01"),
    (1, "INV-1002", 49.0, "paid", "2026-10-01"),
    (1, "INV-1003", 49.0, "paid", "2026-10-01"),  # duplicate charge for October (matches ticket #1)
    (2, "INV-2001", 9.0, "paid", "2026-09-05"),
    (2, "INV-2002", 9.0, "refunded", "2026-10-05"),
    (3, "INV-3001", 499.0, "paid", "2026-09-10"),
    (4, "INV-4001", 49.0, "paid", "2026-08-15"),
    (4, "INV-4002", 49.0, "overdue", "2026-09-15"),
    (4, "INV-4003", 49.0, "overdue", "2026-10-15"),
]
TICKETS = [
    (1, "Charged twice this month", "Hi, I see two charges on my card for October. Can you refund one of them?"),
    (2, "Cannot log in", "I reset my password but I still can't log in. It says my account is locked."),
    (3, "Upgrade to more seats", "We want to add 20 more seats to our plan. How does billing work for that?"),
    (4, "Why was my account suspended?", "My dashboard says my account is past due, but I paid last month. Please help."),
    (1, "Invoice copy needed", "Could you send me a PDF copy of my September invoice for accounting?"),
]


@contextmanager
def get_conn():
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as c:
        c.executescript(SCHEMA)


def seed_if_empty() -> None:
    """Idempotent - safe to call on every startup (free hosts wipe the disk on restart)."""
    init_db()
    with get_conn() as c:
        if c.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            c.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
            c.executemany(
                "INSERT INTO billing (customer_id, invoice_no, amount, status, due_date) VALUES (?,?,?,?,?)", BILLING
            )
            c.executemany("INSERT INTO tickets (customer_id, subject, body) VALUES (?,?,?)", TICKETS)


def _row(r) -> Optional[dict]:
    return dict(r) if r else None


def get_customer(customer_id: int) -> Optional[dict]:
    with get_conn() as c:
        return _row(c.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone())


def get_invoices(customer_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute("SELECT * FROM billing WHERE customer_id=? ORDER BY due_date DESC", (customer_id,)).fetchall()
        return [dict(r) for r in rows]


def list_tickets(status: Optional[str] = None) -> list[dict]:
    with get_conn() as c:
        if status:
            rows = c.execute("SELECT * FROM tickets WHERE status=? ORDER BY id", (status,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_ticket(ticket_id: int) -> Optional[dict]:
    with get_conn() as c:
        return _row(c.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())


def get_customer_tickets(customer_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute("SELECT * FROM tickets WHERE customer_id=? ORDER BY id DESC", (customer_id,)).fetchall()
        return [dict(r) for r in rows]


def save_draft(ticket_id: int, content: str, approved: bool = False) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO drafts (ticket_id, content, approved) VALUES (?,?,?)", (ticket_id, content, int(approved))
        )
        return cur.lastrowid


def mark_ticket_resolved(ticket_id: int) -> None:
    with get_conn() as c:
        c.execute("UPDATE tickets SET status='resolved' WHERE id=?", (ticket_id,))
