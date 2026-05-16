# Activiity Chatbot — Deployment Guide

## Prerequisites

| What | Why | How to get |
|------|-----|------------|
| Python 3.10+ | Run the app | [python.org](https://python.org) |
| OpenRouter API key | Call AI models | [openrouter.ai/keys](https://openrouter.ai/keys) (free tier available) |
| Docker | Run Qdrant (for agentic mode) | [docker.com](https://docker.com) |
| Ollama | Embeddings for Qdrant ingestion | [ollama.com](https://ollama.com) |

---

## 1. Quick Start (Naive mode, no Docker needed)

Naive mode uses a pre-built search index. Everything works out of the box.

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"
python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1
```

Open http://localhost:8788 in your browser.

---

## 2. Agentic Mode Setup (requires Qdrant + Ollama)

Agentic mode routes questions to the right knowledge area before answering. It needs a vector database (Qdrant) and embeddings (Ollama).

### Step 1 — Install & run Ollama

Ollama runs the embedding model locally. Your data never leaves your machine.

```powershell
# Download from https://ollama.com/download and install

# Pull the embedding model (bge-m3 works well for French)
ollama pull bge-m3

# Verify it's running
ollama list
```

### Step 2 — Start Qdrant

Qdrant stores the vector embeddings of all your documents.

```powershell
docker run -d --name activiity-qdrant -p 6333:6333 qdrant/qdrant:v1.11.0
```

Verify: `curl http://localhost:6333/collections` should return a JSON response.

### Step 3 — Ingest the knowledge base into Qdrant

This reads the 28 documents from `data/`, splits them into chunks, generates embeddings via Ollama, and uploads them to Qdrant.

```powershell
# Set required environment variables
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"
$env:EMBED_PROVIDER = "ollama"
$env:OLLAMA_EMBED_MODEL = "bge-m3"
$env:QDRANT_URL = "http://localhost:6333"

# Run ingestion (~30 seconds)
python -m lib.activiity.ingest.cli
```

Expected output:
```
[ingest] QDRANT_URL=http://localhost:6333
...
"points_count": 880
```

Run it once. To re-ingest (e.g. after changing documents):
```powershell
python -m lib.activiity.ingest.cli --force
```

### Step 4 — Start the server

```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"
python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1
```

---

## 3. Using Both Modes

Once the server is running, open http://localhost:8788. In the sidebar:

- **Naive** — works immediately, no extra setup
- **Agentic** — works once Qdrant is running and data is ingested

You can switch between them in the UI. No restart needed.

---

## Docker

```powershell
# Build the image
docker build -t activiity-chatbot .

# Run (naive mode only)
docker run -d -p 8788:8788 --name activiity-chatbot `
  -e OPENROUTER_API_KEY="sk-or-v1-YOUR-KEY" `
  activiity-chatbot

# Run with Qdrant (agentic mode)
docker run -d --name activiity-qdrant -p 6333:6333 qdrant/qdrant:v1.11.0
docker run -d -p 8788:8788 --name activiity-chatbot `
  -e OPENROUTER_API_KEY="sk-or-v1-YOUR-KEY" `
  -e QDRANT_URL="http://host.docker.internal:6333" `
  activiity-chatbot
```

---

## Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | **Required.** OpenRouter API key |
| `LLM_PROVIDER` | `openrouter` | `openrouter` or `ollama` |
| `SLM_MODE` | `0` | `1` = shorter prompts for small models |
| `LLM_MODEL` | `qwen/qwen3-8b` | Default model for generation |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant address (agentic mode) |
| `EMBED_PROVIDER` | `ollama` | Embedding provider for Qdrant |
| `OLLAMA_EMBED_MODEL` | `bge-m3` | Embedding model |

---

## How It Works

```
                    ┌─────────────────────────────┐
                    │     Web UI (localhost:8788)   │
                    └──────────┬──────────────────┘
                               │ your question
                    ┌──────────▼──────────────────┐
                    │       Server (FastAPI)       │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼───────┐  ┌────▼───────┐  ┌────▼───────┐
     │  Naive mode     │  │Agentic mode│  │  Chat mode  │
     │                 │  │            │  │            │
     │ Pre-built index │  │ Qdrant     │  │ Conversation│
     │ + LLM call      │  │ + ReAct    │  │ memory      │
     └─────────────────┘  └────────────┘  └────────────┘
```

**Naive** = one vector search over all documents → one LLM call. Fast, simple.

**Agentic** = ReAct agent decides which knowledge area is relevant → searches only that area → generates answer. More accurate for specific questions.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` | Bad API key | Check your key: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer YOUR-KEY"` |
| Agentic mode says "Qdrant collection not found" | Data not ingested | Run `python -m lib.activiity.ingest.cli` |
| "Connection refused" on Qdrant | Qdrant not running | `docker run -d -p 6333:6333 qdrant/qdrant:v1.11.0` |
| All answers say "not found" | No relevant docs retrieved | For naive: index exists? For agentic: Qdrant ingested? |
| Slow first request | Index loading | Normal — takes ~15s on first startup |
| Docker build copies everything | No `.dockerignore` | Create `.dockerignore` with `.venv`, `.git`, `.qdrant_storage` |


