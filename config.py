"""Central settings. All values can be overridden via environment variables / .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("MEM0_TELEMETRY", "False")  # quiet Mem0 analytics (PostHog) messages

BASE_DIR = Path(__file__).parent


class Settings:
    # --- LLM provider: "openai" (default) or "groq" (free tier) ---
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # Check https://platform.openai.com/docs/models for currently available models
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # --- Embeddings: "openai" (default, tiny cost, no PyTorch) or "local" (free, needs requirements-local.txt) ---
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    local_embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # --- Storage ---
    db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "data" / "support.db"))
    chroma_rag_dir: str = os.getenv("CHROMA_RAG_DIR", str(BASE_DIR / "data" / "chroma_rag"))
    chroma_mem_dir: str = os.getenv("CHROMA_MEM_DIR", str(BASE_DIR / "data" / "chroma_mem0"))
    kb_dir: str = os.getenv("KB_DIR", str(BASE_DIR / "data" / "kb"))

    # --- Behaviour ---
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    memory_top_k: int = int(os.getenv("MEMORY_TOP_K", "3"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    @property
    def llm_model(self) -> str:
        return self.openai_model if self.llm_provider == "openai" else self.groq_model

    @property
    def embedding_dims(self) -> int:
        return 1536 if self.embedding_provider == "openai" else 384  # text-embedding-3-small / all-MiniLM-L6-v2


settings = Settings()
