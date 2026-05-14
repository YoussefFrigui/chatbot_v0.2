FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: install Activiity RAG backend
ARG INSTALL_ACTIVIITY=0
RUN if [ "$INSTALL_ACTIVIITY" = "1" ]; then \
        pip install --no-cache-dir \
            llama-index-core>=0.14 \
            llama-index-llms-openrouter>=0.5 \
            llama-index-embeddings-openai>=0.6 \
            llama-index-vector-stores-qdrant>=0.10 \
            qdrant-client>=1.17; \
    fi

COPY chatbot/ ./chatbot/

EXPOSE 8788

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8788/api/health'); exit(0 if r.status_code==200 else 1)" || exit 1

CMD ["uvicorn", "chatbot.api:app", "--host", "0.0.0.0", "--port", "8788"]