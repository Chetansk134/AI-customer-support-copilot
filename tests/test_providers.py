"""Provider switching (OpenAI / Groq) is pure config logic - testable without any API key."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import copilot  # noqa: E402
import memory  # noqa: E402
from config import settings  # noqa: E402


def test_temperature_omitted_for_reasoning_style_models():
    assert copilot._chat_kwargs("gpt-4o-mini", 0.2) == {"temperature": 0.2}
    assert copilot._chat_kwargs("gpt-5-mini", 0.2) == {}
    assert copilot._chat_kwargs("o4-mini", 0.2) == {}


def test_mem0_config_openai(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    cfg = memory.build_mem0_config()
    assert cfg["llm"]["provider"] == "openai"
    assert cfg["embedder"]["provider"] == "openai"
    assert cfg["embedder"]["config"]["embedding_dims"] == 1536
    assert cfg["vector_store"]["provider"] == "chroma"


def test_mem0_config_groq_with_local_embeddings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "embedding_provider", "local")
    cfg = memory.build_mem0_config()
    assert cfg["llm"]["provider"] == "groq"
    assert cfg["embedder"]["provider"] == "huggingface"
    assert cfg["embedder"]["config"]["embedding_dims"] == 384
