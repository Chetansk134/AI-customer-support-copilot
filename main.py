"""FastAPI routes (Presentation layer)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import database as db
from models import ApproveRequest, DraftResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.seed_if_empty()  # free hosts wipe the disk on restart, so re-seed on startup
    try:
        import rag

        rag.build_index()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] RAG index not built: {exc}")
    yield


app = FastAPI(title="Customer Support Copilot", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tickets")
def list_tickets(status: str | None = None):
    return db.list_tickets(status)


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(404, "ticket not found")
    return {"ticket": ticket, "customer": db.get_customer(ticket["customer_id"])}


@app.post("/tickets/{ticket_id}/draft", response_model=DraftResponse)
def draft_reply(ticket_id: int):
    import copilot

    try:
        return copilot.generate_draft(ticket_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/tickets/{ticket_id}/approve")
def approve(ticket_id: int, body: ApproveRequest):
    import copilot

    try:
        copilot.approve_reply(ticket_id, body.final_reply)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"status": "resolved"}
