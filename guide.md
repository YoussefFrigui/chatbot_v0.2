# Deployment Guide — Activiity Chatbot v0.2

## Requirements

- Python 3.10+
- OpenRouter API key ([free tier](https://openrouter.ai/keys))

## Install & Run

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

## Using the .env file

```powershell
# 1. Copy the example file
copy .env.example .env

# 2. Edit .env and add your key

# 3. Start with the helper script
python start.py
```

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
| **Agentic** | ReAct router → per-UA tools → reranker → synthesis (requires Qdrant) |

## Troubleshooting

- **NotImplementedError** — Restart the server after setting the API key
- **401 Unauthorized** — Check your API key at https://openrouter.ai/keys
- **Slow first request** — Normal, the index is loading (~15s)
