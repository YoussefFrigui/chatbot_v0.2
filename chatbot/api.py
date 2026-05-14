"""FastAPI web API for the Activiity Chatbot v0.2.

Run:
    uvicorn chatbot.api:app --reload --port 8788
    uvicorn chatbot.api:app --host 0.0.0.0 --port 8788  # all interfaces

Endpoints:
    POST /api/chat/ask        — single question (JSON body)
    POST /api/chat/stream     — SSE streaming response
    GET  /api/chat/sessions   — list active sessions
    GET  /api/chat/stats      — session stats
    POST /api/chat/clear      — clear session history
    GET  /api/health          — health check
    GET  /                    — API info page (HTML)
    GET  /docs                — Swagger UI (auto-generated)
    GET  /redoc               — ReDoc documentation
"""
from __future__ import annotations
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field

# Standalone-safe imports — bundled package only
_svc = None
_svc_getter = None

# Add this directory and parent to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from chatbot.config import CFG
except ImportError as exc:
    raise ImportError(
        "chatbot.config is not available from the bundled chatbot_v0.2 package."
    ) from exc

try:
    from chatbot.service import get_chat_service, StreamChunk, ChatResult
    _svc_getter = get_chat_service
except ImportError:
    raise

try:
    _svc = _svc_getter(persist=False)
except Exception:
    _svc = None


app = FastAPI(
    title="Activiity Chatbot v0.2",
    description="Conversational RAG agent over the Activiity knowledge base",
    version="0.2.0",
)

class AskRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=4000,
        description="The question to ask",
    )
    session_id: str | None = Field(
        None,
        description="Session ID for multi-turn conversation (auto-generated if omitted)",
        examples=["abc123-def456"],
    )
    mode: str | None = Field(
        None,
        description="RAG mode: agentic or naive",
        examples=["agentic"],
    )


class AskResponse(BaseModel):
    answer: str
    session_id: str
    rag_mode: str = ""
    model_name: str = ""
    tools_called: list[str] = []
    retrieved_sources: list[str] = []
    iterations: int = 0
    latency_s: float = 0.0
    history_count: int = 0


class StreamEvent(BaseModel):
    delta: str
    is_final: bool
    session_id: str
    meta: dict | None = None


class StatsResponse(BaseModel):
    session_id: str
    n_turns: int
    has_pending: bool
    persisted: bool
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    rag_available: bool
    rag_default_mode: str
    rag_modes: dict[str, bool]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head><title>Activiity Chatbot v0.2</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          max-width: 640px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.5rem; }}
  code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; }}
  ul {{ line-height: 2; padding-left: 1.5rem; }}
  .meta {{ color: #666; font-size: 0.85rem; margin-top: 2rem; }}
</style></head>
<body>
  <h1>🤖 Activiity Chatbot v0.2</h1>
  <p>Conversational RAG agent over the Activiity knowledge base.</p>
  <ul>
    <li><a href="/docs">📖 API Docs (Swagger UI)</a></li>
    <li><a href="/redoc">📘 ReDoc Documentation</a></li>
    <li><code>POST /api/chat/ask</code> — ask a question (one-shot)</li>
    <li><code>POST /api/chat/stream</code> — stream answer via SSE</li>
    <li><code>GET  /api/chat/sessions</code> — list active sessions</li>
    <li><code>GET  /api/chat/stats?sid=&lt;session_id&gt;</code> — session stats</li>
    <li><code>POST /api/chat/clear?sid=&lt;session_id&gt;</code> — clear history</li>
    <li><code>GET  /api/health</code> — health check</li>
  </ul>
  <p class="meta">Built with <a href="https://fastapi.tiangolo.com/">FastAPI</a> +
  <a href="https://www.llamaindex.ai/">LlamaIndex</a> Agentic RAG</p>
</body>
</html>""",
    )


@app.post("/api/chat/ask", response_model=AskResponse, summary="Ask a question")
async def chat_ask(req: AskRequest):
    """Ask a question and get an answer.

    Creates or resumes a conversation session. With a session_id, the
    model has access to previous turns for multi-turn coherence.
    """
    if _svc is None:
        raise HTTPException(
            status_code=503,
            detail="Chat service not available. The bundled RAG backend is not installed.",
        )
    session_id = req.session_id or str(uuid.uuid4())
    result = await _svc.chat(req.question, session_id=session_id, mode=req.mode)
    return AskResponse(
        answer=result.answer,
        session_id=result.session_id,
        rag_mode=result.rag_mode,
        model_name=result.model_name,
        tools_called=result.tools_called,
        retrieved_sources=result.retrieved_sources,
        iterations=result.iterations,
        latency_s=round(result.latency_s, 2),
        history_count=result.history_count,
    )


@app.post("/api/chat/stream", summary="Stream a response")
async def chat_stream(req: AskRequest):
    """Ask a question and receive the answer as Server-Sent Events.

    Client receives a JSON object per SSE event:
    ```json
    {"delta": "...", "is_final": false, "session_id": "..."}
    ```
    """
    session_id = req.session_id or str(uuid.uuid4())

    async def generator():
        try:
            if _svc is None:
                yield f"data: {json.dumps({'error': 'Chat service not available', 'is_final': True})}\n\n"
                return
            async for chunk in _svc.chat_stream(req.question, session_id, mode=req.mode):
                payload = json.dumps(
                    {
                        "delta": chunk.delta,
                        "is_final": chunk.is_final,
                        "session_id": chunk.session_id,
                        "meta": chunk.meta,
                    }
                )
                yield f"data: {payload}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'is_final': True})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/api/chat/sessions", summary="List active sessions")
async def list_sessions():
    """Return all currently active session IDs."""
    if _svc is None:
        return {"sessions": [], "active": 0}
    return {
        "sessions": list(_svc._sessions.keys()),
        "active": len(_svc._sessions),
    }


@app.get("/api/chat/stats", response_model=StatsResponse, summary="Session stats")
async def session_stats(session_id: str = Query(..., description="Session ID")):
    if _svc is None:
        raise HTTPException(status_code=503, detail="Chat service not available.")
    stats = _svc.session_stats(session_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return StatsResponse(
        session_id=stats["session_id"],
        n_turns=stats["n_turns"],
        has_pending=stats["has_pending"],
        persisted=stats["persisted"],
    )


@app.post("/api/chat/clear", summary="Clear session")
async def clear_session(session_id: str = Query(..., description="Session ID")):
    """Clear all conversation history for a session."""
    if _svc is None:
        raise HTTPException(status_code=503, detail="Chat service not available.")
    _svc.clear_session(session_id)
    return {"ok": True, "session_id": session_id}


@app.get("/api/health", response_model=HealthResponse, summary="Health check")
async def health():
    """Check if the service is alive and RAG backend is available."""
    return HealthResponse(
        status="ok",
        service="activiity-chatbot-v0.2",
        timestamp=datetime.now(timezone.utc).isoformat(),
        rag_available=_svc.rag_available if _svc else False,
        rag_default_mode=CFG.rag_mode,
        rag_modes=_svc.rag_modes_available() if _svc else {"agentic": False, "naive": False},
    )