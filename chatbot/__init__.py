"""Activiity Chatbot v0.2 — conversational RAG agent.

Reuses the full Activiity agentic pipeline (AgenticRagService) with
added conversation memory, streaming support, and a FastAPI web API.

Usage:
    # Interactive REPL
    python -m chatbot.cli

    # One-shot question
    python -m chatbot.cli --question "Qu'est-ce que la délégation ?"

    # Web API
    uvicorn chatbot.api:app --reload --port 8788
"""
from __future__ import annotations