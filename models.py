"""Pydantic schemas (Domain layer)."""
from typing import Optional

from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: int
    name: str
    email: str
    plan: str
    status: str


class Ticket(BaseModel):
    id: int
    customer_id: int
    subject: str
    body: str
    status: str = "open"
    created_at: Optional[str] = None


class Invoice(BaseModel):
    id: int
    customer_id: int
    invoice_no: str
    amount: float
    status: str
    due_date: str


class DraftContext(BaseModel):
    """What the copilot used to write the draft - shown in the dashboard's context panel."""
    memories: list[str] = Field(default_factory=list)
    kb_snippets: list[dict] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)


class DraftResponse(BaseModel):
    ticket_id: int
    draft: str
    context: DraftContext


class ApproveRequest(BaseModel):
    final_reply: str = Field(min_length=1, description="The reply the agent actually sent (possibly edited)")
