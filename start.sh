#!/bin/sh
# Runs the FastAPI backend (internal, port 8000) and the Streamlit UI (public, $PORT) in one container.
uvicorn main:app --host 0.0.0.0 --port 8000 &
exec streamlit run app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 --server.headless true
