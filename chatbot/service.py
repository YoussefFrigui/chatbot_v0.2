"""Service layer — wraps the bundled RAG backends.

The chatbot ships with local `lib/baseline` and `lib/activiity` packages,
so it no longer depends on an external parent repo at runtime.

Design:
  - ChatService is the main entry point
  - It wraps AgenticRagService (if available) + SessionMemory
  - Graceful degradation when activiity is missing
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

from chatbot.config import CFG, activiity_available
from chatbot.memory import SessionMemory, Message
from chatbot.prompts import (
    make_chat_system_prompt,
    CHAT_QA_FR,
    CHAT_REFINE_FR,
    CHAT_REFUSAL_FR,
)


@dataclass
class ChatResult:
    answer: str
    session_id: str
    rag_mode: str = ""
    tools_called: list[str] = field(default_factory=list)
    retrieved_sources: list[str] = field(default_factory=list)
    iterations: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    model_name: str = ""
    latency_s: float = 0.0
    history_count: int = 0
    error: str | None = None


@dataclass
class StreamChunk:
    delta: str
    is_final: bool = False
    session_id: str = ""
    meta: dict | None = None


# ---------------------------------------------------------------------------
# Lazy RAG backend
# ---------------------------------------------------------------------------

RAG_MODES = ("agentic", "naive")

_AGENTIC_RAG_CLASS = None
_AGENTIC_RAG_ERROR: str | None = None
_NAIVE_RAG_CLASS = None
_NAIVE_RAG_ERROR: str | None = None


def _get_agentic_class():
    """Lazily import AgenticRagService, caching the result."""
    global _AGENTIC_RAG_CLASS, _AGENTIC_RAG_ERROR
    if _AGENTIC_RAG_CLASS is not None:
        return _AGENTIC_RAG_CLASS
    if _AGENTIC_RAG_ERROR is not None:
        return None
    try:
        from lib.activiity.rag.service import AgenticRagService
        _AGENTIC_RAG_CLASS = AgenticRagService
        return _AGENTIC_RAG_CLASS
    except Exception as e:
        _AGENTIC_RAG_ERROR = f"{type(e).__name__}: {e}"
        return None


def _get_naive_class():
    """Lazily import NaiveRagService, caching the result."""
    global _NAIVE_RAG_CLASS, _NAIVE_RAG_ERROR
    if _NAIVE_RAG_CLASS is not None:
        return _NAIVE_RAG_CLASS
    if _NAIVE_RAG_ERROR is not None:
        return None
    try:
        from lib.baseline.service import NaiveRagService
        _NAIVE_RAG_CLASS = NaiveRagService
        return _NAIVE_RAG_CLASS
    except Exception as e:
        _NAIVE_RAG_ERROR = f"{type(e).__name__}: {e}"
        return None


def _normalize_mode(mode: str | None) -> str:
    value = (mode or CFG.rag_mode or "agentic").strip().lower()
    return value if value in RAG_MODES else "agentic"


def _rag_import_error(mode: str) -> str | None:
    if mode == "naive":
        return _NAIVE_RAG_ERROR
    return _AGENTIC_RAG_ERROR


def _setup_instructions(mode: str) -> str:
    if mode == "naive":
        return (
            "Naive RAG backend not installed.\n"
            "Make sure the bundled `lib/baseline` package and its dependencies are installed.\n"
        )
    return (
        "Agentic RAG backend not installed.\n"
        "Make sure the bundled `lib/activiity` package and its dependencies are installed.\n"
    )


def _make_mock_result(
    question: str,
    latency: float,
    mode: str,
    error: str | None = None,
) -> ChatResult:
    rag_mode = _normalize_mode(mode)
    err_msg = error or _rag_import_error(rag_mode) or "rag backend unavailable"
    return ChatResult(
        answer=(
            f"RAG backend for mode '{rag_mode}' is not available. "
            "Install the bundled dependencies and try again."
        ),
        session_id="mock",
        rag_mode=rag_mode,
        iterations=0,
        latency_s=latency,
        model_name=f"mock-{rag_mode}",
        error=err_msg,
    )


def _node_source(node) -> str:
    if hasattr(node, "metadata") and isinstance(node.metadata, dict):
        return node.metadata.get("source_path", "")
    if hasattr(node, "node") and hasattr(node.node, "metadata"):
        return node.node.metadata.get("source_path", "")
    return ""


# ---------------------------------------------------------------------------
# ChatService
# ---------------------------------------------------------------------------

class ChatService:
    """Conversational RAG agent with persistent memory.

    Features:
    - Multi-turn conversation with sliding window memory
    - Optional RAG backend via activiity (AgenticRagService)
    - SQLite session persistence
    - Simulated token streaming for UI feedback

    Usage:
        svc = ChatService(persist=True)
        result = await svc.chat("Qu'est-ce que la délégation ?")
        async for chunk in svc.chat_stream("..."):
            print(chunk.delta, end="")
    """

    def __init__(self, persist: bool = True):
        self._rag_by_mode: dict[str, object] = {}
        self._rag_errors: dict[str, str] = {}
        self._sessions: dict[str, SessionMemory] = {}
        self._persist = persist
        self._init_rag()

    def _init_rag(self):
        default_mode = _normalize_mode(None)
        self._get_rag(default_mode)

    @property
    def rag_available(self) -> bool:
        return self.rag_available_for(CFG.rag_mode)

    def rag_available_for(self, mode: str) -> bool:
        rag_mode = _normalize_mode(mode)
        if rag_mode in self._rag_by_mode:
            return True
        if rag_mode in self._rag_errors:
            return False
        if _rag_import_error(rag_mode):
            return False
        if rag_mode == "naive":
            return _get_naive_class() is not None
        return _get_agentic_class() is not None

    def rag_modes_available(self) -> dict[str, bool]:
        return {mode: self.rag_available_for(mode) for mode in RAG_MODES}

    def rag_error_for(self, mode: str) -> str | None:
        rag_mode = _normalize_mode(mode)
        if rag_mode in self._rag_errors:
            return self._rag_errors[rag_mode]
        return _rag_import_error(rag_mode)

    def _get_rag(self, mode: str) -> object | None:
        rag_mode = _normalize_mode(mode)
        if rag_mode in self._rag_by_mode:
            return self._rag_by_mode[rag_mode]
        if rag_mode in self._rag_errors:
            return None
        if rag_mode == "naive":
            cls = _get_naive_class()
        else:
            cls = _get_agentic_class()
        if cls is None:
            self._rag_errors[rag_mode] = _rag_import_error(rag_mode) or "backend not installed"
            return None
        try:
            self._rag_by_mode[rag_mode] = cls()
            return self._rag_by_mode[rag_mode]
        except Exception as e:
            self._rag_errors[rag_mode] = f"{type(e).__name__}: {e}"
            return None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str | None) -> SessionMemory:
        if session_id is None:
            session_id = "default"
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemory(
                session_id=session_id,
                persist=self._persist,
            )
        return self._sessions[session_id]

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        question: str,
        session_id: str | None = None,
        mode: str | None = None,
    ) -> ChatResult:
        """Single-turn chat with memory. Returns answer + metadata."""
        mem = self._get_session(session_id)
        t0 = time.perf_counter()
        rag_mode = _normalize_mode(mode)

        # Record user message
        user_msg = mem.add_user_message(question)

        # Build history-aware system prompt
        history_text = mem.get_history_text()
        _system_prompt = make_chat_system_prompt(
            history_text=history_text,
            max_tokens=CFG.max_history_turns * 50,
        )

        # Check RAG availability
        rag = self._get_rag(rag_mode)
        if rag is None:
            latency = time.perf_counter() - t0
            mock = _make_mock_result(question, latency, rag_mode, self.rag_error_for(rag_mode))
            mem.add_assistant_message(mock.answer)
            return mock

        try:
            result = await rag.achat_with_trace(question, history_text=history_text)  # type: ignore[attr-defined]
            latency = time.perf_counter() - t0

            answer = result.answer
            if answer.strip().startswith("Je ne trouve pas"):
                answer = CHAT_REFUSAL_FR

            mem.add_assistant_message(answer)

            sources = []
            for n in result.retrieved_nodes:
                src = _node_source(n)
                if src:
                    sources.append(src)

            return ChatResult(
                answer=answer,
                session_id=mem.session_id,
                rag_mode=rag_mode,
                tools_called=result.tools_called,
                retrieved_sources=sources,
                iterations=result.iterations,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                model_name=str(result.model_name),
                latency_s=latency,
                history_count=len(mem._history),
            )

        except Exception as e:
            fallback_answer = (
                f"Désolé, une erreur s'est produite : {type(e).__name__}. "
                f"Veuillez réessayer ou reformuler votre question."
            )
            latency = time.perf_counter() - t0
            mem.add_assistant_message(fallback_answer)
            return ChatResult(
                answer=fallback_answer,
                session_id=mem.session_id,
                rag_mode=rag_mode,
                tools_called=[],
                retrieved_sources=[],
                iterations=0,
                tokens_in=0,
                tokens_out=0,
                model_name="error",
                latency_s=latency,
                history_count=len(mem._history),
                error=f"{type(e).__name__}: {e}",
            )

    async def chat_stream(
        self,
        question: str,
        session_id: str | None = None,
        mode: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream the RAG answer via simulated token-by-token chunks."""
        result = await self.chat(question, session_id, mode)
        words = result.answer.split()
        chunk = ""
        for i, word in enumerate(words):
            chunk += (word if i == 0 else " " + word) + " "
            is_final = i == len(words) - 1
            if (i + 1) % 3 == 0 or i == len(words) - 1:
                meta = None
                if is_final:
                    meta = {
                        "model_name": result.model_name,
                        "tools_called": result.tools_called,
                        "retrieved_sources": result.retrieved_sources,
                        "iterations": result.iterations,
                        "latency_s": result.latency_s,
                        "history_count": result.history_count,
                        "rag_mode": result.rag_mode,
                    }
                yield StreamChunk(
                    delta=chunk,
                    is_final=is_final,
                    session_id=result.session_id,
                    meta=meta,
                )
                chunk = ""

    def clear_session(self, session_id: str = "default"):
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def session_stats(self, session_id: str = "default") -> dict:
        if session_id in self._sessions:
            return self._sessions[session_id].get_stats()
        return {"error": "session not found"}


# ---------------------------------------------------------------------------
# Global singleton (used by CLI + API)
# ---------------------------------------------------------------------------

_chat_svc: ChatService | None = None


def get_chat_service(persist: bool = True) -> ChatService:
    global _chat_svc
    if _chat_svc is None:
        _chat_svc = ChatService(persist=persist)
    return _chat_svc