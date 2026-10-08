FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Embeddings use the OpenAI API by default, so no PyTorch / local model is needed (small image, low RAM).
# For local embeddings, also run: pip install -r requirements-local.txt and set EMBEDDING_PROVIDER=local

COPY . .

EXPOSE 8501
CMD ["sh", "start.sh"]
