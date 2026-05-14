Activiity Chatbot v0.2 — Web Application
===========================================

A conversational RAG chatbot with a full-featured web interface built on
the **Technical Precision** design system.

Quick Start
-----------

  # Minimal (no RAG backend — demo mode)
  pip install fastapi uvicorn httpx pydantic
  uvicorn chatbot_v0.2.webapp.server:app --reload --port 8788

  # Full RAG support (requires Activiity installed)
  pip install -e /path/to/Activiitykdb
  uvicorn chatbot_v0.2.webapp.server:app --reload --port 8788 --workers 2

  # Open browser
  http://localhost:8788

Docker
------

  docker build -t activiity-chatbot .
  docker run -p 8788:8788 activiity-chatbot

Endpoints
---------

  GET  /                  → Web UI (SPA)
  GET  /api/config        → Current configuration
  GET  /api/health        → Health check + RAG availability
  GET  /api/preflight     → Pre-flight checks
  POST /api/chat/ask      → One-shot Q&A
  POST /api/chat/stream   → SSE streaming response
  GET  /api/chat/sessions → List active sessions
  GET  /api/chat/stats    → Session statistics
  POST /api/chat/clear    → Clear session history
  DEL  /api/chat/sessions/{id} → Delete session

Files
-----

  webapp/
    server.py    FastAPI server with all API endpoints
    static/
      index.html  Full SPA with Alpine.js + Tailwind CSS
      styles.css  Technical Precision design tokens

  chatbot/
    api.py       API logic (also works standalone via uvicorn chatbot.api:app)
    service.py   ChatService with multi-turn memory
    memory.py    SQLite-backed session memory
    config.py    Env-var configuration
    prompts.py   French SLM prompts
    cli.py       CLI for headless usage