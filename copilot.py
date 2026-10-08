"""Orchestrator (Application layer): Mem0 memory + RAG + LangChain tool calling -> draft reply (OpenAI or Groq)."""
import json
import logging
import time

import database as db
import memory
import rag
from config import settings
from models import DraftContext, DraftResponse
from tools import TOOL_MAP, TOOLS

_llm = None
logger = logging.getLogger("uvicorn.error")  # shows up in the uvicorn terminal


def _chat_kwargs(model: str, temperature: float) -> dict:
    """Newer OpenAI reasoning-style models (gpt-5*, o-series) reject a custom temperature, so omit it for them."""
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        return {}
    return {"temperature": temperature}


def _get_llm():
    global _llm
    if _llm is None:
        if settings.llm_provider == "openai":
            from langchain_openai import ChatOpenAI

            _llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                **_chat_kwargs(settings.openai_model, settings.temperature),
            )
        else:
            from langchain_groq import ChatGroq

            _llm = ChatGroq(model=settings.groq_model, temperature=settings.temperature, api_key=settings.groq_api_key)
    return _llm


def _invoke(runnable, messages):
    """Retry with exponential backoff - free-tier rate limits (HTTP 429) are common."""
    for attempt in range(settings.llm_max_retries):
        try:
            return runnable.invoke(messages)
        except Exception:  # noqa: BLE001
            if attempt == settings.llm_max_retries - 1:
                raise
            time.sleep(2**attempt)


def _gather_with_tools(ticket: dict) -> list[dict]:
    """Let the LLM decide which CRM/billing tools to call for this ticket, then execute them."""
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(
            content="You are a support copilot. Use the available tools to fetch the customer context "
            "needed to answer the ticket. Call every tool that is relevant. Do not write the reply yet."
        ),
        HumanMessage(content=f"Customer id: {ticket['customer_id']}\nSubject: {ticket['subject']}\n{ticket['body']}"),
    ]
    ai = _invoke(_get_llm().bind_tools(TOOLS), messages)
    results = []
    for call in getattr(ai, "tool_calls", []) or []:
        tool = TOOL_MAP.get(call["name"])
        if tool is None:
            continue
        output = tool.invoke(call["args"])
        results.append({"tool": call["name"], "args": call["args"], "output": json.loads(output)})
    return results


def _write_draft(ticket: dict, memories: list[str], kb: list[dict], tool_results: list[dict]) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    kb_text = "\n\n".join(f"[{s['source']}] {s['text']}" for s in kb) or "none"
    mem_text = "\n".join(f"- {m}" for m in memories) or "none"
    tool_text = json.dumps(tool_results, indent=2) if tool_results else "none"
    system = (
        "You are a customer support copilot writing a DRAFT reply for a human agent to review.\n"
        "Rules:\n"
        "1. Use ONLY facts from the context below. Never invent refunds, dates, amounts or policies.\n"
        "2. Check the customer's claims against the CRM / billing data. That data counts as the confirmation the "
        "policies ask for. If it confirms the claim, say what you found (invoice numbers, dates, amounts) and give the "
        "resolution the policy prescribes (for example a refund and its timeframe). Do NOT ask the customer for "
        "information the data already provides. Only if the data does NOT confirm the claim, say what you do see and "
        "ask for the specific details needed.\n"
        "3. State the concrete next step and timeframe from the policy when one applies, and include every option the "
        "policy gives (for example waiting for an automatic unlock as well as an agent unlock).\n"
        "4. Mention only facts relevant to the customer's issue. Do not comment on unrelated account or billing data, "
        "and do not speculate about causes the data does not show.\n"
        "5. Be polite and concise. Start with 'Hi <customer first name>,'. Write only the email body (no subject line, "
        "no filler like 'please allow me a moment' or 'thank you for your patience'). Sign off as 'Support Team'.\n"
        "6. You cannot attach or send files yourself. Never say a file is attached or included. Instead say what the "
        "agent will do (for example email the invoice) or where the customer can find it, as described in the knowledge base."
    )
    user = (
        f"TICKET\nSubject: {ticket['subject']}\nMessage: {ticket['body']}\n\n"
        f"CUSTOMER MEMORY\n{mem_text}\n\nKNOWLEDGE BASE\n{kb_text}\n\nCRM / BILLING DATA\n{tool_text}\n\n"
        "Write the reply email body."
    )
    return _invoke(_get_llm(), [SystemMessage(content=system), HumanMessage(content=user)]).content.strip()


def generate_draft(ticket_id: int) -> DraftResponse:
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"ticket {ticket_id} not found")
    query = f"{ticket['subject']} {ticket['body']}"

    try:
        memories = memory.get_memories(ticket["customer_id"], query)
    except Exception as exc:  # noqa: BLE001  (a memory failure should not block the draft, but do log it)
        logger.warning("Memory lookup failed: %r", exc)
        memories = []
    kb = rag.search(query)
    tool_results = _gather_with_tools(ticket)
    draft = _write_draft(ticket, memories, kb, tool_results)

    db.save_draft(ticket_id, draft)
    return DraftResponse(
        ticket_id=ticket_id,
        draft=draft,
        context=DraftContext(memories=memories, kb_snippets=kb, tool_results=tool_results),
    )


def approve_reply(ticket_id: int, final_reply: str) -> None:
    """Agent approved/sent a reply: store it, resolve the ticket, and teach memory what happened."""
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"ticket {ticket_id} not found")
    db.save_draft(ticket_id, final_reply, approved=True)
    db.mark_ticket_resolved(ticket_id)
    memory.add_memory(
        ticket["customer_id"],
        f"Support ticket '{ticket['subject']}': customer said \"{ticket['body']}\". Our reply: {final_reply}",
    )
