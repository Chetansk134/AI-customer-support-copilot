"""Persistent customer memory with Mem0 (open-source) backed by local ChromaDB.
Mem0 uses the configured LLM provider to extract facts, and the configured embedder to index them."""
from config import settings

_memory = None


def build_mem0_config() -> dict:
    """Pure function (easy to test): builds the Mem0 config for the chosen providers."""
    if settings.llm_provider == "openai":
        llm = {"provider": "openai", "config": {"model": settings.openai_model, "temperature": 0.1, "max_tokens": 1000}}
    else:
        llm = {"provider": "groq", "config": {"model": settings.groq_model, "temperature": 0.1, "max_tokens": 1000}}

    if settings.embedding_provider == "openai":
        model = settings.openai_embedding_model
        embedder = {"provider": "openai", "config": {"model": model, "embedding_dims": settings.embedding_dims}}
    else:
        model = settings.local_embedding_model
        embedder = {"provider": "huggingface", "config": {"model": model, "embedding_dims": settings.embedding_dims}}

    return {
        "llm": llm,
        "embedder": embedder,
        "vector_store": {
            "provider": "chroma",
            "config": {"collection_name": "customer_memories", "path": settings.chroma_mem_dir},
        },
    }


def _get_memory():
    global _memory
    if _memory is None:
        from mem0 import Memory

        # Mem0's OpenAI / Groq providers read OPENAI_API_KEY / GROQ_API_KEY from the environment (loaded from .env)
        _memory = Memory.from_config(build_mem0_config())
    return _memory


def _uid(customer_id: int) -> str:
    return f"customer_{customer_id}"


def _search(mem, query: str, uid: str, limit: int):
    """Different Mem0 versions take different search() arguments, so try the newer style first and fall back."""
    attempts = [
        {"filters": {"user_id": uid}, "limit": limit},
        {"filters": {"user_id": uid}, "top_k": limit},
        {"user_id": uid, "limit": limit},  # older Mem0 versions
    ]
    last_error = None
    for kwargs in attempts:
        try:
            return mem.search(query, **kwargs)
        except (TypeError, ValueError) as exc:
            last_error = exc
    raise last_error


def get_memories(customer_id: int, query: str, limit: int | None = None) -> list[str]:
    """Search this customer's long-term memories relevant to the query."""
    res = _search(_get_memory(), query, _uid(customer_id), limit or settings.memory_top_k)
    items = res.get("results", []) if isinstance(res, dict) else res  # Mem0 versions differ in return shape
    return [i["memory"] for i in items if "memory" in i]


def add_memory(customer_id: int, text: str):
    """Store something worth remembering about this customer.
    Mem0 first tries to extract facts with the LLM; if it finds nothing worth keeping (common for support-ticket
    notes), we store the note verbatim so the memory is never silently lost."""
    mem = _get_memory()
    res = mem.add([{"role": "user", "content": text}], user_id=_uid(customer_id))
    stored = res.get("results", []) if isinstance(res, dict) else (res or [])
    if not stored:
        res = mem.add(text, user_id=_uid(customer_id), infer=False)
    return res
