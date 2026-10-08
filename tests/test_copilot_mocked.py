"""Tests the orchestrator wiring with a fake LLM, fake memory and fake RAG (no network / API key needed)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "mock.db")

from langchain_core.messages import AIMessage  # noqa: E402

import copilot  # noqa: E402
import database as db  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def bind_tools(self, tools):
        outer = self

        class Bound:
            def invoke(self, messages):
                return AIMessage(
                    content="",
                    tool_calls=[{"name": "get_billing_info", "args": {"customer_id": 1}, "id": "call_1"}],
                )

        return Bound()

    def invoke(self, messages):
        self.prompts.append(messages[-1].content)
        return AIMessage(content="Hi Aarav, we have refunded the duplicate charge. Support Team")


def test_generate_draft_uses_memory_rag_and_tools(monkeypatch):
    db.seed_if_empty()
    fake = FakeLLM()
    monkeypatch.setattr(copilot, "_get_llm", lambda: fake)
    monkeypatch.setattr(copilot.memory, "get_memories", lambda cid, q, limit=None: ["Prefers email over phone"])
    monkeypatch.setattr(copilot.rag, "search", lambda q, k=None: [{"source": "refund-policy.md", "text": "Duplicate charges are refunded."}])

    res = copilot.generate_draft(1)

    assert res.draft.startswith("Hi Aarav")
    assert res.context.memories == ["Prefers email over phone"]
    assert res.context.kb_snippets[0]["source"] == "refund-policy.md"
    assert res.context.tool_results[0]["tool"] == "get_billing_info"
    # everything made it into the final prompt
    prompt = fake.prompts[0]
    assert "Prefers email over phone" in prompt and "Duplicate charges" in prompt and "INV-1001" in prompt


def test_approve_resolves_ticket_and_saves_memory(monkeypatch):
    db.seed_if_empty()
    saved = []
    monkeypatch.setattr(copilot.memory, "add_memory", lambda cid, text: saved.append((cid, text)))
    copilot.approve_reply(2, "We unlocked your account.")
    assert db.get_ticket(2)["status"] == "resolved"
    assert saved and saved[0][0] == 2
