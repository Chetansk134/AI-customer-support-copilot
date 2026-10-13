# AI-Powered Customer Support Copilot

An AI-assisted customer support application that gathers relevant customer information, retrieves answers from a support knowledge base, remembers useful details from previous interactions, and generates an editable reply for a support agent to review and approve.

The project demonstrates how **Retrieval-Augmented Generation (RAG), persistent customer memory, and LLM tool calling** can work together in a practical support workflow.

## Key Features

- **Ticket dashboard:** Browse sample support tickets, filter by open or resolved status, and view ticket and customer details.
- **AI-generated reply drafts:** Generate a contextual reply for a selected ticket and edit it before approval.
- **Knowledge-base retrieval (RAG):** Retrieve relevant passages from Markdown support documents using ChromaDB vector search.
- **Persistent customer memory:** Use Mem0 with ChromaDB to store and retrieve useful customer-specific details across interactions.
- **Tool calling:** Let the language model request customer-profile, billing, and ticket-history lookups through LangChain tools.
- **Human approval:** Review and edit a draft before approving it; approval resolves the ticket and records a memory note.
- **Configurable LLM provider:** Use OpenAI by default or switch to Groq through environment settings.
- **REST API:** FastAPI exposes endpoints for health checks, ticket retrieval, draft generation, and approval.
- **Testing and deployment support:** Includes pytest tests, Docker configuration, and a Render Blueprint file.

> **Important:** This repository uses a sample SQLite CRM/billing dataset and mock lookup tools. It is a demonstration project, not connected to a real CRM, payment system, or email-sending service. “Approve & send” approves the reply in the app and resolves the ticket; it does not send an actual email.

## Technology Stack

| Component | Technologies |
|---|---|
| User interface | Streamlit |
| Backend API | FastAPI, Uvicorn |
| LLM orchestration and tools | LangChain, LangChain OpenAI / Groq integrations |
| Language models | OpenAI (default) or Groq (optional) |
| Retrieval-augmented generation | ChromaDB, LangChain text splitters |
| Customer memory | Mem0, ChromaDB |
| Data storage | SQLite |
| Configuration | Python, `python-dotenv`, environment variables |
| Testing | pytest, FastAPI TestClient, Streamlit AppTest |
| Deployment | Docker, Docker Compose, Render configuration |

## How It Works

1. A support agent selects a ticket from the Streamlit dashboard.
2. The application loads the ticket and the associated customer profile from SQLite.
3. The copilot searches customer memory and the support knowledge base for relevant context.
4. The configured LLM decides which available tools are useful and can retrieve customer profile, billing records, or ticket history.
5. The copilot combines the ticket, retrieved knowledge, customer memories, and tool results to generate a draft reply.
6. The agent reviews and edits the draft, then chooses **Approve & send**.
7. The ticket is marked resolved and a note about the interaction is saved to customer memory.

## Architecture

```text
Streamlit Dashboard (app.py)
          |
          | HTTP requests
          v
FastAPI REST API (main.py)
          |
          v
Copilot Orchestrator (copilot.py)
     |          |           |
     v          v           v
Customer      RAG /       LangChain
Memory        Knowledge   Tool Calling
(memory.py)   Base        (tools.py)
              (rag.py)       |
     |          |            v
     v          v       Mock CRM / Billing
   ChromaDB   ChromaDB    lookups via SQLite
                              |
                              v
                         database.py
                              |
                              v
                           SQLite
```

## Project Structure

```text
support-copilot/
├── app.py                  # Streamlit support-agent dashboard
├── main.py                 # FastAPI routes and startup lifecycle
├── copilot.py              # Draft-generation orchestration and approval workflow
├── rag.py                  # Knowledge-base indexing and semantic search
├── memory.py               # Mem0 customer-memory integration
├── tools.py                # LangChain CRM, billing, and ticket-history tools
├── database.py             # SQLite schema, sample data, and data-access functions
├── config.py               # Environment-based settings
├── models.py               # Pydantic request/response schemas
├── data/
│   └── kb/                 # Markdown knowledge-base documents (add your own here)
├── tests/                  # API, database, tool, provider, copilot, and UI tests
├── requirements.txt        # Core dependencies
├── requirements-local.txt  # Optional local embedding dependencies
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── start.sh
└── .env.example            # Environment-variable template
```

## Prerequisites

- Python 3.11 recommended (the included Dockerfile uses Python 3.11).
- An API key for your selected LLM provider.
- Git (optional, for cloning the repository).

## Run Locally

### 1. Open the project directory

```bash
cd support-copilot
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and edit `.env` with your provider settings.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

For the default OpenAI configuration, set your key and model:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
```

Alternatively, configure Groq for chat completions:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_PROVIDER=openai
```

The application uses OpenAI embeddings by default even when Groq is the chat provider, so an OpenAI key is still needed for that configuration. To use local embeddings instead, install `requirements-local.txt` and set `EMBEDDING_PROVIDER=local`; this downloads and uses a local embedding model and may require more memory and disk space.

**Never commit `.env` or publish API keys.** Keep `.env.example` limited to placeholder values.

### 5. Start the API

From the `support-copilot` directory, run:

```bash
uvicorn main:app --reload
```

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

The API startup initializes the SQLite sample data and attempts to build the knowledge-base index.

### 6. Start the dashboard

Open a **second terminal**, activate the same virtual environment, move to the project directory, and run:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

If the API runs at a different address, set `API_URL` in the dashboard environment, for example `API_URL=http://127.0.0.1:8000`.

## Run with Docker

1. Create a local `.env` file from `.env.example` and configure your API key.
2. From the directory containing `docker-compose.yml`, run:

```bash
docker compose up --build
```

The dashboard is available at `http://localhost:8501`, and the API documentation is available at `http://localhost:8000/docs`.

To stop the services, press `Ctrl+C`, or run `docker compose down` in another terminal.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check whether the API is running |
| `GET` | `/tickets` | List support tickets |
| `GET` | `/tickets?status=open` | Filter tickets by status |
| `GET` | `/tickets/{ticket_id}` | Get a ticket and its customer profile |
| `POST` | `/tickets/{ticket_id}/draft` | Generate a draft reply using memory, RAG, and tools |
| `POST` | `/tickets/{ticket_id}/approve` | Approve a reply, resolve the ticket, and update memory |

Example approval request body:

```json
{
  "final_reply": "Hello, thanks for contacting support. We have reviewed your request..."
}
```

## Add Knowledge-Base Documents

1. Add support-policy or FAQ documents as `.md` files in the directory configured by `KB_DIR` (by default, `data/kb/`).
2. Restart the API so the startup lifecycle can build the index, or call `rag.build_index(force=True)` from a Python session when you need to rebuild an existing index.
3. Keep the documents accurate, concise, and free of confidential customer information.

The RAG pipeline splits Markdown documents into overlapping chunks and stores their embeddings in ChromaDB. The number of retrieved snippets can be adjusted with `RAG_TOP_K`.

## Run Tests

Run the test suite from the project directory:

```bash
pytest
```

The tests cover the SQLite seed data, data-access functions, tool registry, API routes, provider configuration, mocked copilot draft generation, approval behavior, and dashboard flows. Most tests use mocked LLM behavior and do not require a live model call; real end-to-end draft generation does require valid provider credentials and a working embedding configuration.

## Useful Configuration

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | Chat model provider (`openai` or `groq`) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | OpenAI chat model | `gpt-4o-mini` |
| `GROQ_API_KEY` | Groq API key | — |
| `GROQ_MODEL` | Groq chat model | `llama-3.3-70b-versatile` |
| `EMBEDDING_PROVIDER` | Embedding provider (`openai` or `local`) | `openai` |
| `OPENAI_EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |
| `EMBEDDING_MODEL` | Local Hugging Face embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `DB_PATH` | SQLite database file path | `data/support.db` |
| `KB_DIR` | Knowledge-base directory | `data/kb` |
| `CHROMA_RAG_DIR` | ChromaDB directory for RAG vectors | `data/chroma_rag` |
| `CHROMA_MEM_DIR` | ChromaDB directory for customer memory | `data/chroma_mem0` |
| `RAG_TOP_K` | Number of knowledge-base snippets to retrieve | `3` |
| `MEMORY_TOP_K` | Number of customer memories to retrieve | `3` |
| `LLM_MAX_RETRIES` | Number of LLM invocation attempts | `3` |

## Deployment Notes

The repository includes `render.yaml` for a Render Blueprint deployment. Review the service configuration before deploying, set secrets through the hosting provider's environment settings, and verify that the selected plan provides persistent storage if you need customer memories and database data to survive restarts. Ephemeral filesystems may lose SQLite and ChromaDB data when a service restarts or redeploys.

## Limitations and Future Improvements

- Replace sample CRM and billing lookups with authenticated integrations to real systems.
- Add authentication, authorization, rate limiting, and audit logging before exposing the app publicly.
- Add a real outbound email or help-desk integration if replies need to be sent externally.
- Add persistent-volume or managed database/vector-store configuration for production deployments.
- Add safeguards and evaluation for retrieved content, tool arguments, sensitive data, and generated replies.
- Add broader monitoring, structured logging, and end-to-end integration tests.

## License

No license file is included in this repository. Add a `LICENSE` file if you intend to distribute the project under a specific open-source license.
