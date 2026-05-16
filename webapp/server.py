"""Activiity Chatbot v0.2 — Web Application Server.

Run:
    python -m uvicorn webapp.server:app --reload --port 8788

Open http://localhost:8788
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import (
    StreamingResponse, HTMLResponse, FileResponse, JSONResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path setup — handle both standalone and monorepo mode
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
LIB_ROOT = ROOT / "lib"
for _p in [str(ROOT), str(LIB_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Lazy imports — bundled packages only
# ---------------------------------------------------------------------------

_svc_getter = None
_stream_chunk_cls = None
_chat_result_cls = None

try:
    from chatbot.service import get_chat_service as _svc_getter
    from chatbot.service import StreamChunk as _stream_chunk_cls
    from chatbot.service import ChatResult as _chat_result_cls
except ImportError:
    raise ImportError("chatbot.service is not available in the bundled chatbot_v0.2 package.")

StreamChunk = _stream_chunk_cls
ChatResult = _chat_result_cls

# ChatConfig — standalone-safe config
from dataclasses import dataclass, field
@dataclass
class _StandaloneCfg:
    llm_provider = "openrouter"
    openrouter_model = "qwen/qwen3-8b"
    synth_model = "qwen/qwen3-8b"
    slm_mode = False
    max_iterations = 2
    use_reranker = False
    embed_provider = "ollama"
    qdrant_url = "http://localhost:6333"
    _rag_mode = "naive"
    openrouter_api_key = ""
    @property
    def rag_mode(self): return os.getenv("CHAT_RAG_MODE", self._rag_mode)

_svc = _svc_getter() if _svc_getter else None
CFG = _StandaloneCfg()
try:
    from chatbot.config import CFG as _CFG, CHAT
    CFG = _CFG
except ImportError:
    pass

# Eval helpers
ragas_for_single = None
try:
    from eval.metrics.ragas_bridge import ragas_for_single
except ImportError:
    pass

load_tier = None
try:
    from eval.parser import load_tier
except ImportError:
    pass

from webapp.demo_catalog import (
    catalog, default_agentic_router, default_agentic_synths,
    default_model_id, find_model, routers_for_agentic, synths_for_agentic,
)

MODEL_RUNNER = ROOT / "webapp" / "model_runner.py"


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

STATIC = ROOT / "webapp" / "static"
STATIC.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Activiity Chatbot v0.2",
    description="Conversational RAG agent over the Activiity knowledge base. Compare SLMs with live RAGAS evaluation.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Lazy-loaded RAG service (loads index on first use, not at import)
_naive_rag: object | None = None
def _get_naive_rag():
    global _naive_rag
    if _naive_rag is None:
        try:
            from lib.baseline.service import NaiveRagService
            _naive_rag = NaiveRagService()
        except Exception:
            _naive_rag = "__unavailable__"
    return _naive_rag if _naive_rag != "__unavailable__" else None

_agentic_rag: object | None = None
def _get_agentic_rag():
    global _agentic_rag
    if _agentic_rag is None:
        try:
            from lib.activiity.rag.service import AgenticRagService
            _agentic_rag = AgenticRagService()
        except Exception:
            _agentic_rag = "__unavailable__"
    return _agentic_rag if _agentic_rag != "__unavailable__" else None

try:
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
except Exception:
    pass  # already mounted or not needed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_key(s: str) -> str:
    if not s or len(s) < 8:
        return "***"
    return f"{s[:6]}...{s[-4:]}"


def _pair_to_dict(pair) -> dict:
    return {
        "id": pair.id,
        "tier": pair.tier,
        "bucket": pair.bucket,
        "question": pair.question,
        "ground_truth": pair.ground_truth,
        "tags": list(pair.tags) if hasattr(pair, 'tags') else [],
    }


def _pairs_for_tier(tier: str) -> list[dict]:
    if load_tier is None:
        return []
    return [_pair_to_dict(p) for p in load_tier(tier)]


async def _run_model_subprocess(payload: dict) -> dict:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(MODEL_RUNNER),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(ROOT),
        env={**os.environ, **payload.pop("_env", {})},
    )
    stdout, stderr = await proc.communicate(json.dumps(payload).encode("utf-8"))
    if proc.returncode not in (0, None):
        err = stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(err or f"model runner exited with code {proc.returncode}")
    if not stdout:
        raise RuntimeError("model runner returned no output")
    envelope = json.loads(stdout.decode("utf-8"))
    if not envelope.get("ok"):
        raise RuntimeError(envelope.get("error", "model runner failed"))
    return envelope["result"]


async def _compute_ragas(question: str, answer: str, ground_truth: str,
                          contexts: list[str], model_id: str) -> dict:
    if ragas_for_single is None:
        return {"model_id": model_id, "error": "ragas not available"}
    try:
        result = await ragas_for_single(question, answer, ground_truth, contexts)
        result["model_id"] = model_id
        return result
    except Exception as e:
        return {"model_id": model_id, "error": str(e)}


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/chat")
async def chat_page():
    return await index()


@app.get("/sessions")
async def sessions_page():
    return await index()


@app.get("/settings")
async def settings_page():
    return await index()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ChatConfigResponse(BaseModel):
    llm_provider: str
    openrouter_model: str
    synth_model: str
    slm_mode: bool
    max_iterations: int
    use_reranker: bool
    embed_provider: str
    qdrant_url: str
    rag_available: bool
    rag_mode_default: str
    rag_modes: dict[str, bool]
    model_catalog: dict
    model_defaults: dict
    model_defaults_multi: dict


class ChatPairResponse(BaseModel):
    id: str
    tier: str
    bucket: str
    question: str
    ground_truth: str
    tags: list[str]


class ModelScoreResponse(BaseModel):
    model_id: str
    model_name: str
    mode: str
    answer: str
    tools_called: list[str]
    retrieved_sources: list[str]
    retrieved_chunks: list[str]
    iterations: int
    latency_s: float
    tokens_in: int
    tokens_out: int
    ragas: dict = Field(default_factory=dict)


class CompareResponse(BaseModel):
    session_id: str
    tier: str
    mode: str
    question: str
    ground_truth: str
    history: str = ""
    results: list[ModelScoreResponse]


class AskResponse(BaseModel):
    answer: str
    session_id: str
    rag_mode: str
    tools_called: list[str]
    iterations: int
    tokens_in: int
    tokens_out: int
    model_name: str
    latency_s: float
    error: str | None = None


class ConfigUpdateRequest(BaseModel):
    api_key: str | None = None
    router_model: str | None = None
    synth_model: str | None = None
    use_reranker: bool | None = None
    mode: str | None = None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/config", response_model=ChatConfigResponse)
async def get_config():
    rag_modes = _svc.rag_modes_available() if _svc else {"agentic": False, "naive": False}
    return ChatConfigResponse(
        llm_provider=CFG.llm_provider,
        openrouter_model=CFG.openrouter_model,
        synth_model=CFG.synth_model,
        slm_mode=CFG.slm_mode,
        max_iterations=CFG.max_iterations,
        use_reranker=CFG.use_reranker,
        embed_provider=CFG.embed_provider,
        qdrant_url=CFG.qdrant_url,
        rag_available=_svc.rag_available if _svc else False,
        rag_mode_default=CFG.rag_mode,
        rag_modes=rag_modes,
        model_catalog=catalog(),
        model_defaults={
            "naive": default_model_id("naive"),
            "agentic": default_agentic_router(),
        },
        model_defaults_multi={
            "agentic_synths": default_agentic_synths(),
        },
    )


@app.post("/api/config", response_model=ChatConfigResponse)
async def set_config(cfg: ConfigUpdateRequest):
    """Update runtime config (API key, etc.). Values applied immediately."""
    import os as _os
    if cfg.api_key:
        _os.environ["OPENROUTER_API_KEY"] = cfg.api_key
    if cfg.router_model:
        _os.environ["LLM_MODEL"] = cfg.router_model
    if cfg.synth_model:
        _os.environ["SYNTH_MODEL"] = cfg.synth_model
    if cfg.use_reranker is not None:
        _os.environ["USE_RERANKER"] = "1" if cfg.use_reranker else "0"
    return ChatConfigResponse(
        llm_provider=CFG.llm_provider,
        openrouter_model=CFG.openrouter_model,
        synth_model=CFG.synth_model,
        slm_mode=CFG.slm_mode,
        max_iterations=CFG.max_iterations,
        use_reranker=CFG.use_reranker,
        embed_provider=CFG.embed_provider,
        qdrant_url=CFG.qdrant_url,
        rag_available=_svc.rag_available if _svc else False,
        rag_mode_default=CFG.rag_mode,
        rag_modes=_svc.rag_modes_available() if _svc else {"agentic": False, "naive": False},
        model_catalog=catalog(),
        model_defaults={
            "naive": default_model_id("naive"),
            "agentic": default_agentic_router(),
        },
        model_defaults_multi={
            "agentic_synths": default_agentic_synths(),
        },
    )


@app.get("/api/chat/pairs", response_model=list[ChatPairResponse])
async def get_chat_pairs(tier: str = Query(..., pattern="^(reference|medium|advanced)$")):
    return _pairs_for_tier(tier)


OR_API = "https://openrouter.ai/api/v1/chat/completions"

async def _call_openrouter(model_id: str, prompt: str, api_key: str) -> dict:
    """Direct OpenRouter API call - no subprocess, no llama-index."""
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            OR_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.2,
            },
        )
        latency = time.perf_counter() - t0
        if resp.status_code != 200:
            return {"answer": f"[error] OpenRouter HTTP {resp.status_code}", "latency_s": latency, "tokens_in": 0, "tokens_out": 0}
        data = resp.json()
        return {
            "answer": data["choices"][0]["message"]["content"],
            "latency_s": latency,
            "tokens_in": data.get("usage", {}).get("prompt_tokens", 0),
            "tokens_out": data.get("usage", {}).get("completion_tokens", 0),
        }


@app.post("/api/chat/compare", response_model=CompareResponse)
async def compare_models(req: Request):
    body = await req.json()

    mode = body.get("mode", "naive")
    models = body.get("models", [])
    router_model = body.get("router_model") or ""
    question = body.get("question", "")
    tier = body.get("tier", "reference")
    history = body.get("history", "")
    api_key = body.get("api_key") or os.getenv("OPENROUTER_API_KEY", "")
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key

    # Find ground truth
    pairs = _pairs_for_tier(tier)
    pair = next((p for p in pairs if p.get("question", "").strip() == question.strip()), None)
    ground_truth = body.get("ground_truth") or (pair.get("ground_truth", "") if pair else "")

    if not api_key:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not set")

    # Get model list
    if mode == "naive":
        model_ids = models
    else:
        model_ids = body.get("synth_models") or default_agentic_synths()

    if not model_ids:
        raise HTTPException(status_code=400, detail="No models selected")

    # Naive RAG mode: retrieve + generate in-process
    if mode == "naive":
        rag = _get_naive_rag()
        if rag is None:
            raise HTTPException(status_code=503, detail="NaiveRAG service not available (check lib/baseline/)")

        async def _run_naive(model_id: str) -> dict:
            model = find_model(mode, model_id)
            label = model.label if model else model_id
            try:
                result = await rag.achat_with_trace(question, history_text=history, model_override=model_id)
                nodes = getattr(result, "retrieved_nodes", [])
                sources = []
                chunks = []
                for n in nodes:
                    meta = getattr(n, "metadata", None) or {}
                    src = meta.get("source_path", "")
                    if src: sources.append(src)
                    text = getattr(n, "text", None) or ""
                    if text: chunks.append(text)
                return {
                    "model_id": model_id,
                    "model_name": label,
                    "mode": mode,
                    "answer": result.answer,
                    "latency_s": result.ttft_s or 0,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "tools_called": result.tools_called,
                    "retrieved_sources": sources,
                    "retrieved_chunks": chunks,
                    "iterations": result.iterations,
                }
            except Exception as e:
                return {
                    "model_id": model_id, "model_name": label, "mode": mode,
                    "answer": f"[error] {type(e).__name__}: {e}",
                    "latency_s": 0, "tokens_in": 0, "tokens_out": 0,
                    "tools_called": [], "retrieved_sources": [], "retrieved_chunks": [], "iterations": 0,
                }

        raw_results = await asyncio.gather(*[_run_naive(m) for m in model_ids])
    else:
        # Agentic: ReActAgent (with direct-API synthesizer) or simple fallback
        _agentic_svc = _get_agentic_rag()

        if _agentic_svc is None:
            # Fallback: simple_agentic (no ReAct, just classify + retrieve)
            try:
                from lib.activiity.rag.simple_agentic import run_agentic
            except ImportError:
                async def _err(m: str) -> dict:
                    model = find_model(mode, m); label = model.label if model else m
                    if router_model:
                        r = find_model(mode, router_model); label = f"{r.label} → {label}" if r else label
                    return {"model_id": m, "model_name": label, "mode": mode, "answer": "[error] Agentic mode unavailable (Qdrant not running or not installed).", "latency_s": 0, "tokens_in": 0, "tokens_out": 0, "tools_called": [], "retrieved_sources": [], "retrieved_chunks": [], "iterations": 0}
                raw_results = await asyncio.gather(*[_err(m) for m in model_ids])
            else:
                async def _run_simple(synth_id: str) -> dict:
                    model = find_model(mode, synth_id); label = model.label if model else synth_id
                    if router_model:
                        r = find_model(mode, router_model); label = f"{r.label} → {label}" if r else label
                    try:
                        result = await run_agentic(router_model or "qwen/qwen3-8b", synth_id, question, api_key)
                        return {"model_id": synth_id, "model_name": label, "mode": mode, "answer": result.answer, "latency_s": result.latency_s, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out, "tools_called": result.tools_called, "retrieved_sources": result.sources, "retrieved_chunks": result.chunks, "iterations": result.iterations}
                    except Exception as e:
                        return {"model_id": synth_id, "model_name": label, "mode": mode, "answer": f"[error] {type(e).__name__}: {e}", "latency_s": 0, "tokens_in": 0, "tokens_out": 0, "tools_called": [], "retrieved_sources": [], "retrieved_chunks": [], "iterations": 0}
                raw_results = await asyncio.gather(*[_run_simple(m) for m in model_ids])
        else:
            # Use ReActAgent
            async def _run_react(synth_id: str) -> dict:
                model = find_model(mode, synth_id); label = model.label if model else synth_id
                if router_model:
                    r = find_model(mode, router_model); label = f"{r.label} → {label}" if r else label
                try:
                    result = await _agentic_svc.achat_with_trace(question)
                    nodes = list(getattr(result, "retrieved_nodes", []) or [])
                    sources = []
                    chunks = []
                    for n in nodes:
                        meta = getattr(n, "metadata", None) or {}
                        src = meta.get("source_path", "")
                        if src: sources.append(src)
                        text = getattr(n, "text", None) or ""
                        if text: chunks.append(text)
                    return {"model_id": synth_id, "model_name": label, "mode": mode, "answer": result.answer, "latency_s": result.ttft_s or 0, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out, "tools_called": list(result.tools_called), "retrieved_sources": sources, "retrieved_chunks": chunks, "iterations": result.iterations}
                except Exception as e:
                    return {"model_id": synth_id, "model_name": label, "mode": mode, "answer": f"[error] {type(e).__name__}: {e}", "latency_s": 0, "tokens_in": 0, "tokens_out": 0, "tools_called": [], "retrieved_sources": [], "retrieved_chunks": [], "iterations": 0}
            raw_results = await asyncio.gather(*[_run_react(m) for m in model_ids])

    results: list[ModelScoreResponse] = []
    for item in raw_results:
        model_id = item.get("model_id", "")
        model = find_model(mode, model_id)
        results.append(ModelScoreResponse(
            model_id=model_id,
            model_name=item.get("model_name") or (model.label if model else model_id),
            mode=item.get("mode", mode),
            answer=item.get("answer", ""),
            tools_called=list(item.get("tools_called", [])),
            retrieved_sources=list(item.get("retrieved_sources", [])),
            retrieved_chunks=list(item.get("retrieved_chunks", [])),
            iterations=int(item.get("iterations", 0) or 0),
            latency_s=float(item.get("latency_s", 0) or 0),
            tokens_in=int(item.get("tokens_in", 0) or 0),
            tokens_out=int(item.get("tokens_out", 0) or 0),
            ragas={},
        ))

    return CompareResponse(
        session_id=str(uuid.uuid4()),
        tier=tier,
        mode=mode,
        question=question,
        ground_truth=ground_truth,
        history=history,
        results=results,
    )


@app.post("/api/chat/ragas")
async def compute_ragas(req: Request):
    body = await req.json()
    result = await _compute_ragas(
        body.get("question", ""),
        body.get("answer", ""),
        body.get("ground_truth", ""),
        body.get("contexts", []),
        body.get("model_id", ""),
    )
    return result


@app.post("/api/chat/ask", response_model=AskResponse)
async def chat_ask(req: Request):
    body = await req.json()
    question = body.get("question", "")
    session_id = body.get("session_id")
    mode = body.get("mode")

    if _svc is None:
        return AskResponse(
            answer="Chat service not available. Install the bundled chatbot dependencies.",
            session_id=session_id or "default",
            rag_mode=mode or "unknown",
            tools_called=[],
            iterations=0,
            tokens_in=0,
            tokens_out=0,
            model_name="none",
            latency_s=0.0,
            error="service unavailable",
        )

    # Propagate API key if provided
    if body.get("api_key"):
        os.environ["OPENROUTER_API_KEY"] = body["api_key"]

    t0 = time.perf_counter()
    try:
        result = await _svc.chat(question, session_id=session_id, mode=mode)
        return AskResponse(
            answer=result.answer,
            session_id=result.session_id,
            rag_mode=result.rag_mode,
            tools_called=result.tools_called,
            iterations=result.iterations,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            model_name=result.model_name,
            latency_s=result.latency_s,
            error=result.error,
        )
    except Exception as e:
        return AskResponse(
            answer=f"Error: {type(e).__name__}: {e}",
            session_id=session_id or "default",
            rag_mode=mode or "unknown",
            tools_called=[],
            iterations=0,
            tokens_in=0,
            tokens_out=0,
            model_name="error",
            latency_s=time.perf_counter() - t0,
            error=str(e),
        )


@app.post("/api/chat/ask/stream")
async def ask_stream(req: Request):
    """Stream a single model answer directly from OpenRouter (no ChatService)."""
    body = await req.json()
    model_id = body.get("model") or body.get("model_id", "")
    question = body.get("question", "")
    api_key = body.get("api_key") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or not question or not model_id:
        return JSONResponse({"error": "model, question, and api_key required"}, status_code=400)

    async def gen():
        yield f"data: {json.dumps({'type': 'meta', 'model': model_id})}\n\n"
        try:
            async with httpx.AsyncClient(timeout=180) as c:
                async with c.stream("POST", OR_API,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_id, "messages": [{"role": "user", "content": question}], "max_tokens": 1024, "temperature": 0.2, "stream": True},
                ) as resp:
                    if resp.status_code != 200:
                        yield f"data: {json.dumps({'type': 'error', 'text': f'HTTP {resp.status_code}'})}\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            payload = line[6:].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                chunk = json.loads(payload)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield f"data: {json.dumps({'type': 'token', 'text': delta})}\n\n"
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/chat/stream")
async def chat_stream(req: Request):
    body = await req.json()
    question = body.get("question", "")
    session_id = body.get("session_id")
    mode = body.get("mode")

    if body.get("api_key"):
        os.environ["OPENROUTER_API_KEY"] = body["api_key"]

    if _svc is None:
        async def fallback():
            yield "data: " + json.dumps({"error": "service unavailable"}, ensure_ascii=False) + "\n\n"
        return StreamingResponse(fallback(), media_type="text/event-stream")

    async def gen():
        try:
            async for chunk in _svc.chat_stream(question, session_id=session_id, mode=mode):
                data = {
                    "delta": chunk.delta,
                    "is_final": chunk.is_final,
                    "session_id": chunk.session_id,
                }
                if chunk.meta:
                    data.update(chunk.meta)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/chat/sessions")
async def list_sessions():
    if _svc is None:
        return []
    return list(_svc._sessions.keys())


@app.get("/api/chat/stats")
async def session_stats(session_id: str = "default"):
    if _svc is None:
        return {"error": "service unavailable"}
    return _svc.session_stats(session_id)


@app.post("/api/chat/clear")
async def clear_session(session_id: str = "default"):
    if _svc:
        _svc.clear_session(session_id)
    return {"ok": True, "session_id": session_id}


@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in (_svc._sessions if _svc else {}):
        del _svc._sessions[session_id]
    return {"ok": True}


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "status": "ok",
        "rag": {
            "rag_available": _svc.rag_available if _svc else False,
            "rag_modes": _svc.rag_modes_available() if _svc else {},
            "agentic_error": _svc.rag_error_for("agentic") if _svc else None,
            "naive_error": _svc.rag_error_for("naive") if _svc else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sessions_active": len(_svc._sessions) if _svc else 0,
    }


@app.get("/api/preflight")
async def preflight():
    """Check prerequisites for running."""
    issues = []
    if not _svc or not _svc.rag_available:
        issues.append({
            "severity": "error",
            "message": "RAG backend not available. Install activiity or ensure lib/ is resolvable.",
        })
    if not CFG.openrouter_api_key and CFG.llm_provider == "openrouter":
        issues.append({
            "severity": "warning",
            "message": "No OPENROUTER_API_KEY set — cloud LLMs won't work.",
        })
    return {
        "ok": all(i["severity"] != "error" for i in issues),
        "all_passed": all(i["severity"] != "error" for i in issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Static file fallbacks
# ---------------------------------------------------------------------------

@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve any static file, fallback to index.html (SPA routing)."""
    f = STATIC / path
    if f.exists() and f.is_file():
        return FileResponse(f)
    return await index()