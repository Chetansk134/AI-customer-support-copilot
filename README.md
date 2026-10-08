# AI-Powered Customer Support Copilot

Agent that gathers customer context (RAG + Mem0 memory + LangChain tool calling) and drafts a reply in one click.
Stack: FastAPI, SQLite, ChromaDB, Mem0, LangChain, OpenAI (or free Groq), Streamlit, Docker, GitHub Actions, Render.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then paste your OpenAI key into .env (or switch to Groq, see the file)
pytest                                                # DB / tools / API / dashboard tests (no LLM needed)
uvicorn main:app --reload                             # terminal 1 - API docs at http://127.0.0.1:8000/docs
streamlit run app.py                                  # terminal 2 - dashboard at http://localhost:8501
```

## Run with Docker
```bash
docker compose up --build        # dashboard on :8501, API on :8000
```

## Deploy free on Render
1. Push this repo to GitHub (public repos get free GitHub Actions minutes).
2. In Render: New > Blueprint > pick the repo (it reads `render.yaml`), add `OPENAI_API_KEY` when asked.
3. Every push to `main` redeploys after CI passes. The free tier sleeps when idle, so open the app a minute before a demo.
4. Data is re-seeded on every startup (`database.seed_if_empty`, `rag.build_index`) because free hosts wipe the disk.

## Architecture
`app.py` (Streamlit) and `main.py` (FastAPI routes) -> `copilot.py` (orchestrator: memory + RAG + tools -> draft)
-> `memory.py` (Mem0 + Chroma), `rag.py` (KB -> Chroma), `tools.py` (mock CRM/billing) -> `database.py` (SQLite)
Settings in `config.py`, schemas in `models.py`. `start.sh` runs API + UI in one container.
