"""Run a single demo model in an isolated subprocess.

Keeps per-request model overrides isolated from the parent FastAPI
process so parallel comparisons do not race on global config state.

Standalone: uses the bundled `lib/baseline` and `lib/activiity` packages.
If dependencies are missing, returns a graceful error response so the web
UI can display "model unavailable" cards.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LIB_ROOT = ROOT / "lib"
for _p in [str(ROOT), str(LIB_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from webapp.demo_catalog import find_model  # noqa: E402


def _actual_model_id(model_id: str) -> str:
    return model_id


def _patch_agentic_config(router_model: str, synth_model: str, use_reranker: bool) -> bool:
    """Patch the bundled agentic config. Returns True on success."""
    try:
        from lib.activiity.config import EVAL_CONFIG
        EVAL_CONFIG["router_model"] = router_model
        EVAL_CONFIG["synth_model"] = synth_model
        EVAL_CONFIG["use_reranker"] = use_reranker
        return True
    except ImportError:
        return False


async def _run(payload: dict) -> dict:
    mode = (payload.get("mode") or "naive").strip().lower()
    model_id = payload.get("model_id") or ""
    router_model = payload.get("router_model") or ""
    question = payload.get("question") or ""
    # Optional session history (previous user questions and assistant replies)
    history = payload.get("history") or ""
    use_reranker = bool(payload.get("use_reranker", False))

    # Apply request-scoped env vars (API key from UI input)
    request_env = payload.pop("_env", {})
    for k, v in request_env.items():
        if v:
            os.environ[k] = v

    model = find_model(mode, model_id)
    router = find_model(mode, router_model) if router_model else None
    if model is None and mode == "agentic":
        model = router
    if model is None:
        raise ValueError(f"Unknown model_id for mode {mode!r}: {model_id!r}")

    t0 = time.perf_counter()

    if mode == "naive":
        try:
            from lib.baseline.service import NaiveRagService
        except ImportError:
            return _make_unavailable_result(
                mode=mode,
                model_id=model.model_id,
                model_label=model.label if model else model_id,
                reason="NaiveRagService not available in the bundled chatbot_v0.2 package.",
                latency=time.perf_counter() - t0,
            )

        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["LLM_MODEL"] = _actual_model_id(model.model_id)
        svc = NaiveRagService()
        result = await svc.achat_with_trace(question, history_text=history)

    elif mode == "agentic":
        synth_model = model_id
        if not router_model:
            raise ValueError("router_model is required for agentic mode")
        synth = find_model(mode, synth_model)
        if synth is None:
            raise ValueError(f"Unknown synth model for agentic mode: {synth_model!r}")

        patched = _patch_agentic_config(
            router_model=router_model,
            synth_model=synth_model,
            use_reranker=use_reranker,
        )
        if not patched:
            # Standalone mode — AgenticRagService not available
            return _make_unavailable_result(
                mode=mode,
                model_id=f"{router_model}::{model_id}",
                model_label=f"{router.label if router else router_model} → {model.label if model else model_id}",
                reason="activiity.rag.service (AgenticRagService) not installed in the bundled chatbot_v0.2 package.",
                latency=time.perf_counter() - t0,
            )

        try:
            from lib.activiity.rag.service import AgenticRagService
        except ImportError:
            return _make_unavailable_result(
                mode=mode,
                model_id=f"{router_model}::{model_id}",
                model_label=f"{router.label if router else router_model} → {model.label if model else model_id}",
                reason="AgenticRagService not available in the bundled chatbot_v0.2 package.",
                latency=time.perf_counter() - t0,
            )

        svc = AgenticRagService()
        result = await svc.achat_with_trace(question, history_text=history)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    latency = time.perf_counter() - t0
    retrieved_nodes = list(getattr(result, "retrieved_nodes", []))
    retrieved_sources: list[str] = []
    retrieved_chunks: list[str] = []
    for node in retrieved_nodes:
        metadata = getattr(node, "metadata", None) or getattr(getattr(node, "node", None), "metadata", {}) or {}
        source_path = metadata.get("source_path", "")
        if source_path:
            retrieved_sources.append(source_path)
        text = getattr(node, "text", None) or getattr(getattr(node, "node", None), "text", "")
        if text:
            retrieved_chunks.append(text)

    return {
        "model_id": f"{router_model}::{model_id}" if mode == "agentic" else model.model_id,
        "mode": mode,
        "model_name": (
            f"{router.label} → {model.label}"
            if mode == "agentic" and router and model
            else (model.label if model else model_id)
        ),
        "answer": getattr(result, "answer", ""),
        "tools_called": list(getattr(result, "tools_called", [])),
        "retrieved_sources": retrieved_sources,
        "retrieved_chunks": retrieved_chunks,
        "iterations": int(getattr(result, "iterations", 0) or 0),
        "latency_s": round(latency, 3),
        "tokens_in": int(getattr(result, "tokens_in", 0) or 0),
        "tokens_out": int(getattr(result, "tokens_out", 0) or 0),
    }


def _make_unavailable_result(mode: str, model_id: str, model_label: str, reason: str, latency: float) -> dict:
    return {
        "model_id": model_id,
        "mode": mode,
        "model_name": model_label,
        "answer": f"[Module not available] {reason}",
        "tools_called": [],
        "retrieved_sources": [],
        "retrieved_chunks": [],
        "iterations": 0,
        "latency_s": round(latency, 3),
        "tokens_in": 0,
        "tokens_out": 0,
        "unavailable": True,
        "error": reason,
    }


async def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw or "{}")
    try:
        result = await _run(payload)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))