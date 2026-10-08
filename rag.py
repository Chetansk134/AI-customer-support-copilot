"""RAG over the support knowledge base: markdown docs -> ChromaDB (OpenAI or local embeddings)."""
from pathlib import Path

from config import settings

_vectorstore = None


def _get_embeddings():
    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    from langchain_huggingface import HuggingFaceEmbeddings  # needs requirements-local.txt

    return HuggingFaceEmbeddings(model_name=settings.local_embedding_model)


def _get_vectorstore():
    """Lazy-load heavy deps so the API starts fast and tests don't need them."""
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma

        embeddings = _get_embeddings()
        _vectorstore = Chroma(
            collection_name="support_kb",
            embedding_function=embeddings,
            persist_directory=settings.chroma_rag_dir,
        )
    return _vectorstore


def build_index(force: bool = False) -> int:
    """Load KB markdown files, chunk them and index them. Returns number of chunks in the index."""
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    vs = _get_vectorstore()
    existing = vs._collection.count()
    if existing and not force:
        return existing
    if existing and force:
        vs.delete_collection()
        global _vectorstore
        _vectorstore = None
        vs = _get_vectorstore()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    docs = []
    for path in sorted(Path(settings.kb_dir).glob("*.md")):
        for chunk in splitter.split_text(path.read_text(encoding="utf-8")):
            docs.append(Document(page_content=chunk, metadata={"source": path.name}))
    if docs:
        vs.add_documents(docs)
    return len(docs)


def search(query: str, k: int | None = None) -> list[dict]:
    """Return top-k KB snippets as [{'source':..., 'text':...}]."""
    vs = _get_vectorstore()
    results = vs.similarity_search(query, k=k or settings.rag_top_k)
    return [{"source": d.metadata.get("source", "kb"), "text": d.page_content} for d in results]
