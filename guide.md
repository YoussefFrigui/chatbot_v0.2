# Deployment Guide — Activiity Chatbot v0.2

## Requirements

- Python 3.10+
- OpenRouter API key ([free tier](https://openrouter.ai/keys))

## Install & Run

### Option A — Environment variable (quick start)

```powershell
# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"

# Start server
python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1
```

Open http://localhost:8788 in your browser.

### Option B — Using the .env file

```powershell
# 1. Copy the example file
copy .env.example .env

# 2. Edit .env and add your key

# 3. Start with the helper script
python start.py
```

### Option C — Enter API key in the UI

Start the server without setting a key, then enter it in the browser:

1. `python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1`
2. Open http://localhost:8788
3. Paste your key into the sidebar field and click **Save**

## Verify It's Running

```powershell
Invoke-WebRequest -Uri http://localhost:8788/api/config
```

Expected: JSON with `"rag_available": true`

## Web UI

| Tab | Purpose |
|-----|---------|
| Workbench | Select models, enter question, run comparison |
| History | View past conversations (search, filter, export) |

### Settings
Enter your OpenRouter API key in the sidebar and click **Save**.

## Modes

| Mode | Description |
|------|-------------|
| **Naive** | Retrieve from vector store → generate answer (works standalone) |
| **Agentic** | ReAct router → per-UA tools → reranker → synthesis (requires Qdrant + ingested data) |

## Ingestion (for Agentic mode)

The naive mode uses a pre-built index (no setup needed). Agentic mode requires Qdrant with ingested data:

```powershell
# 1. Start Qdrant
docker run -d --name activiity-qdrant -p 6333:6333 qdrant/qdrant:v1.11.0

# 2. Ingest documents
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY"
$env:EMBED_PROVIDER = "ollama"
$env:OLLAMA_EMBED_MODEL = "bge-m3"
$env:QDRANT_URL = "http://localhost:6333"
python -m lib.activiity.ingest.cli
```

This embeds the 28 documents from `data/` and uploads them to Qdrant. Only needed once.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **NotImplementedError** | Restart the server after setting the API key |
| **401 Unauthorized** | Verify your key: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer YOUR-KEY"` |
| **No models work** | Check `lib/baseline` is present (for naive) or Qdrant is running (for agentic) |
| **Slow first request** | Normal — the index is loading (~15s) |
