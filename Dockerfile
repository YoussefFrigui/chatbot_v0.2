FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire application
COPY . .

# Remove dev-only files
RUN rm -rf .venv .git .gitignore .qdrant_storage __pycache__ .pytest_cache && \
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8788

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8788/api/health',timeout=5); exit(0 if r.status_code==200 else 1)" || exit 1

CMD ["uvicorn", "webapp.server:app", "--host", "0.0.0.0", "--port", "8788"]
