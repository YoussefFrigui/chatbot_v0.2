"""Chat v0.2 README — usage and architecture."""
from __future__ import annotations

README = """
# Activiity Chatbot v0.2

Conversational RAG agent built on the Activiity knowledge base.
Wraps the existing AgenticRagService with conversation memory,
a CLI, and a FastAPI web API.

## Architecture

```
chatbot_v0.2/
├── chatbot/
│   ├── __init__.py      # Package init
│   ├── config.py         # Chatbot config (inherits activiity EVAL_CONFIG)
│   ├── memory.py         # SessionMemory (SQLite-backed sliding window)
│   ├── prompts.py        # Chat-adapted French prompts
│   ├── service.py        # ChatService (wraps AgenticRagService)
│   ├── cli.py            # Interactive REPL / one-shot CLI
│   └── api.py            # FastAPI web API
├── README.md             # This file

## Quick Start

```bash
# 1. Ensure the Qdrant index is built
python -m activiity.ingest.cli

# 2. Interactive chat (REPL)
python -m chatbot.cli

# 3. One-shot question
python -m chatbot.cli --question "Qu'est-ce que la délégation efficace ?"

# 4. Start the web API
uvicorn chatbot.api:app --reload --port 8788

# 5. Test via curl
curl -X POST http://localhost:8788/api/chat/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Quels sont les 5 principes de la délégation ?"}'
```

## Configuration

All settings inherit from `activiity.config.EVAL_CONFIG`. Chatbot overrides:
- `router_model`: qwen/qwen3-14b (for ReAct routing)
- `synth_model`: qwen/qwen3-8b (for answer synthesis)
- `slm_mode`: True (optimized prompts)
- `max_iterations`: 2
- `use_reranker`: False
- `max_history_turns`: 10 (per session)

Environment variables:
- `CHAT_MAX_HISTORY` — override max history turns
- `CHAT_HISTORY_IN_SYSTEM` — "1" to include history in system prompt
- `CHAT_STREAM` — "1" to enable streaming output
- `CHAT_PERSIST_DIR` — custom session storage path
- `OPENROUTER_API_KEY` — API key for cloud LLMs

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/` | HTML landing page |
| GET    | `/api/health` | Health check |
| POST   | `/api/chat/ask` | Ask a question (one-shot) |
| POST   | `/api/chat/stream` | Stream answer via SSE |
| GET    | `/api/chat/sessions` | List active sessions |
| GET    | `/api/chat/stats` | Session statistics |
| POST   | `/api/chat/clear` | Clear session history |

## Session Memory

Each session maintains a sliding window of the last 10 turns.
History is injected into the system prompt so the LLM maintains
conversational context across turns. Sessions are persisted to
SQLite in `chatbot/sessions/<session_id>.db`.

## Integration with Existing Eval Pipeline

The chatbot reuses:
- `activiity.rag.service.AgenticRagService` — the full ReAct pipeline
- `activiity.providers.factory.build_llm` / `build_synth_llm` — LLM setup
- `activiity.prompts.defaults_fr` — base SLM prompts
- `activiity.config.CFG` — all base configuration
"""