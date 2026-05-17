# Activiity Chatbot — Deployment Guide

This guide is for one unified chatbot run where both modes are available at the same time.

- You run one server process.
- In the UI, you can switch between `Naive` and `Agentic` anytime.

## Prerequisites

| What | Why | How to get |
|------|-----|------------|
| Python 3.12+ | Local run and ingestion scripts | [python.org](https://python.org) |
| OpenRouter API key | Model inference | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Docker | Qdrant service (agentic) | [docker.com](https://docker.com) |
| Ollama | Embedding service (runs in its own Docker container) | Pulled automatically via `docker compose`. For local runs: [ollama.com](https://ollama.com) → `ollama pull bge-m3` |
| OpenAI API key | Alternative embedding provider (no Ollama needed) | [platform.openai.com](https://platform.openai.com) — set `EMBED_PROVIDER=openai` |

---

## 1) Unified Local Run (Naive + Agentic Together)

### Step A — Install and set API key

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"
```

### Step B — Start Qdrant (for agentic)

```powershell
docker run -d --name activiity-qdrant -p 6333:6333 qdrant/qdrant:latest
```

Quick check:

```powershell
curl http://localhost:6333/collections
```

### Step C — Install and configure embedding provider

**Why this is required:** Both naive and agentic modes need to embed user questions into vectors to search the knowledge base. The embedding happens at query time (not just during ingestion). Without a running embedding service, the chatbot cannot retrieve documents and will return errors like `Failed to connect to Ollama`.

Option 1 (recommended local): Ollama

```powershell
ollama pull bge-m3
ollama list

$env:EMBED_PROVIDER = "ollama"
$env:OLLAMA_EMBED_MODEL = "bge-m3"
```

Option 2: OpenAI embeddings

```powershell
$env:EMBED_PROVIDER = "openai"
$env:OPENAI_API_KEY = "YOUR-OPENAI-KEY"
$env:OPENAI_EMBED_MODEL = "text-embedding-3-small"
```

### Step D — Ingest Qdrant once (agentic requirement)

```powershell
$env:QDRANT_URL = "http://localhost:6333"
python -m lib.activiity.ingest.cli
```

Re-ingest if needed:

```powershell
python -m lib.activiity.ingest.cli --force
```

### Step E — Run the chatbot once (both modes enabled)

```powershell
python -m uvicorn webapp.server:app --host 127.0.0.1 --port 8788
```

Open http://localhost:8788 and switch mode in the sidebar.

Naive ingestion note:

- Naive mode does not need ingestion for normal startup because `baseline/.index/` is already committed.
- Only rebuild naive index if you changed files under `data/`.

Optional naive index rebuild:

```powershell
python -c "from lib.baseline.index import build_index; build_index()"
```

---

## 2) Docker Compose (3 containers: chatbot + Ollama + Qdrant)

Three separate containers, each doing one thing:

| Container | Image | Role |
|-----------|-------|------|
| `activiity-chatbot` | Built from `Dockerfile` | Web UI + API |
| `activiity-ollama` | `ollama/ollama` | Embeddings (bge-m3) |
| `activiity-qdrant` | `qdrant/qdrant` | Vector store (agentic) |

**Important ordering:** Start infrastructure first (Ollama + Qdrant), prepare them (pull model + ingest), then start the chatbot last. If the chatbot starts before Ollama has bge-m3, embedding calls will fail.

### Step 1 — Start the infrastructure containers

```powershell
# Start only Qdrant and Ollama (not the chatbot yet)
docker compose up -d qdrant ollama
```

### Step 2 — Pull the embedding model in Ollama

Without this step, the chatbot cannot embed questions and will return errors.

```powershell
docker exec activiity-ollama ollama pull bge-m3
```

Verify:
```powershell
docker exec activiity-ollama ollama list
```
You should see `bge-m3` in the list.

### Step 3 — Ingest the knowledge base into Qdrant

This reads the 28 documents from `data/`, splits them into chunks, embeds them via Ollama, and uploads to Qdrant. Required for agentic mode.

Since the chatbot container is not running yet, run ingestion from your host machine:

```powershell
$env:QDRANT_URL = "http://localhost:6333"
$env:EMBED_PROVIDER = "ollama"
$env:OLLAMA_EMBED_MODEL = "bge-m3"
python -m lib.activiity.ingest.cli
```

Expected output:
```
[ingest] QDRANT_URL=http://localhost:6333
...
"points_count": 880
```

Only needed once. To re-ingest after changing documents:
```powershell
python -m lib.activiity.ingest.cli --force
```

### Step 4 — Build and start the chatbot (LAST)

Only do this after the previous steps complete.

```powershell
# Build the chatbot image
docker compose build chatbot

# Start the chatbot container
docker compose up -d chatbot
```

Open http://localhost:8788. Both naive and agentic modes work.

### Step 5 — Verify everything

```powershell
# Check all 3 containers are running
docker ps

# Test the health endpoint
curl http://localhost:8788/api/health

# Test naive mode gives a real answer (not an Ollama error)
curl -X POST http://localhost:8788/api/chat/compare -H "Content-Type: application/json" -d '{"mode":"naive","models":["qwen/qwen3-8b"],"question":"Quels sont les quatre sources de frustration du manager qui délègue ?","tier":"reference"}'
```

### If you don't want Docker Compose (manual)

```powershell
# Step 1: Infrastructure
docker run -d --name activiity-qdrant -p 6333:6333 qdrant/qdrant:latest
docker run -d --name activiity-ollama -p 11434:11434 ollama/ollama:latest

# Step 2: Pull embedding model
docker exec activiity-ollama ollama pull bge-m3

# Step 3: Ingest Qdrant
$env:QDRANT_URL = "http://localhost:6333"
$env:EMBED_PROVIDER = "ollama"
$env:OLLAMA_EMBED_MODEL = "bge-m3"
python -m lib.activiity.ingest.cli

# Step 4: Start chatbot (LAST)
docker build -t activiity-chatbot .
docker run -d -p 8788:8788 --name activiity-chatbot `
  -e OPENROUTER_API_KEY="sk-or-v1-YOUR-KEY" `
  -e QDRANT_URL="http://host.docker.internal:6333" `
  -e OLLAMA_URL="http://host.docker.internal:11434" `
  activiity-chatbot
```

### Stopping everything

```powershell
docker compose down
# Or manually:
docker stop activiity-chatbot activiity-ollama activiity-qdrant
```

---

## 3) Production Checklist

Verify all of the following before go-live:

1. `OPENROUTER_API_KEY` is set in runtime environment.
2. `/api/health` returns `ok: true`.
3. Naive mode answers a reference `UA-1` question with grounded content.
4. Agentic mode answers the same question and does not show `collection not found`.
5. Reverse proxy routes both static UI and `/api/*` on the same origin.
6. Logs do not show repeated `401` or persistent `429` errors.

Smoke tests:

```powershell
curl http://localhost:8788/api/health
curl "http://localhost:8788/api/chat/pairs?tier=reference"
```

Optional mode-specific API smoke tests:

```powershell
curl -Method Post http://localhost:8788/api/chat/compare -ContentType "application/json" -Body '{"mode":"naive","models":["qwen/qwen3-8b"],"question":"Quels sont les cinq principes d\u0027une délégation efficace selon la synthèse Manageris de l\u0027UA-1 ?","tier":"reference"}'
curl -Method Post http://localhost:8788/api/chat/compare -ContentType "application/json" -Body '{"mode":"agentic","router_model":"qwen/qwen3-14b","synth_models":["qwen/qwen3-8b"],"question":"Quels sont les cinq principes d\u0027une délégation efficace selon la synthèse Manageris de l\u0027UA-1 ?","tier":"reference"}'
```

---

## 4) Runtime Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | Required for OpenRouter inference |
| `LLM_PROVIDER` | `openrouter` | Inference provider |
| `LLM_MODEL` | `qwen/qwen3-8b` | Default generation/router model |
| `SYNTH_MODEL` | `qwen/qwen3-14b` | Agentic synthesis model |
| `SLM_MODE` | `0` | Shorter prompts for small models |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint (agentic) |
| `QDRANT_COLLECTION` | `activiity_kb` | Base collection name |
| `EMBED_PROVIDER` | `ollama` | `ollama` or `openai` for ingestion/embedding |
| `OLLAMA_EMBED_MODEL` | `bge-m3` | Ollama embedding model |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |

---

## 5) Troubleshooting

| Problem | Likely cause | Action |
|---------|--------------|--------|
| `401 Unauthorized` from model calls | Invalid/missing OpenRouter key | Set `OPENROUTER_API_KEY` correctly |
| Agentic says `collection not found` | Qdrant not ingested | Run `python -m lib.activiity.ingest.cli` |
| Qdrant connection refused | Service not running/reachable | Start Qdrant and verify `QDRANT_URL` |
| Browser CORS errors in prod | Wrong frontend/backend origin routing | Route UI and `/api/*` through same host/reverse proxy |
| `Failed to connect to Ollama` | Ollama not running or unreachable | Start Ollama (`ollama serve`), pull model (`ollama pull bge-m3`), or switch to `EMBED_PROVIDER=openai` |
| Naive answers empty/weak | Missing/stale baseline index | Ensure `baseline/.index` exists, rebuild only if `data/` changed |
| Slow first request | Cold startup/index warmup | Expected once per process |

---

## 6) Architecture Summary

- Naive: committed local index (`baseline/.index`) + one retrieval + one model call.
- Agentic: router chooses UA tool(s), retrieves from Qdrant, then synthesizes answer.
- Webapp: FastAPI serves both static UI and API; frontend uses relative `/api/*` routes.


