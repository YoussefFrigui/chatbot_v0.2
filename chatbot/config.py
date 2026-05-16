"""Chatbot configuration — fully standalone, env-var driven.

No hard dependency on activiity.config. All values come from environment
variables with sensible defaults. When activiity IS installed, it reads
additional knobs from CFG as fallbacks.

Config precedence:
  1. Direct defaults in CHAT_CONFIG below
  2. Environment variables (see __init__.py docstring)
    3. Bundled `lib/activiity.config.CFG` (if installed)
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

CHAT_CONFIG = {
    "bot_name": "Activiity",
    "bot_description": "Assistant management & coaching — Fiches Protocole UA-1..UA-10",
    "max_history_turns": 10,
    "history_in_system": True,
    "stream_chunks": True,
    "persist_dir": str(Path(__file__).resolve().parent / "sessions"),
    "rag_mode": "agentic",

    # LLM
    "llm_provider": "openrouter",
    "openrouter_api_key": "",
    "openrouter_model": "qwen/qwen3-14b",
    "ollama_base_url": "http://localhost:11434",
    "ollama_llm_model": "qwen2.5:14b-instruct",
    "llm_temperature": 0.2,

    # Synthesis model (two-LLM split)
    "synth_model": "qwen/qwen3-8b",
    "use_synth_custom": True,

    # Embeddings
    "embed_provider": "ollama",
    "openai_api_key": "",
    "openai_embed_model": "text-embedding-3-small",
    "ollama_embed_model": "bge-m3",

    # RAG / agent
    "slm_mode": False,
    "max_iterations": 2,
    "use_reranker": False,
    "reranker_model": "BAAI/bge-reranker-v2-m3",
    "rerank_top_k": 20,
    "rerank_keep": 5,
    "top_k_per_ua": 5,
    "top_k_global": 8,

    # Vector store
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "activiity_kb",

    # Chunking
    "chunk_size": 512,
    "chunk_overlap": 64,
}


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class ChatCfg:
    """Typed chatbot configuration with env-var overrides."""

    @property
    def bot_name(self) -> str:
        return _env("CHAT_BOT_NAME", CHAT_CONFIG["bot_name"])

    @property
    def bot_description(self) -> str:
        return _env("CHAT_BOT_DESC", CHAT_CONFIG["bot_description"])

    @property
    def max_history_turns(self) -> int:
        return int(_env("CHAT_MAX_HISTORY", str(CHAT_CONFIG["max_history_turns"])))

    @property
    def history_in_system(self) -> bool:
        return _env("CHAT_HISTORY_IN_SYSTEM", "1" if CHAT_CONFIG["history_in_system"] else "0") == "1"

    @property
    def stream_chunks(self) -> bool:
        return _env("CHAT_STREAM", "1" if CHAT_CONFIG["stream_chunks"] else "0") == "1"

    @property
    def persist_dir(self) -> Path:
        return Path(_env("CHAT_PERSIST_DIR", CHAT_CONFIG["persist_dir"]))

    @property
    def rag_mode(self) -> str:
        return _env("CHAT_RAG_MODE", CHAT_CONFIG["rag_mode"]).lower()

    # --- LLM ---
    @property
    def llm_provider(self) -> str:
        return _env("LLM_PROVIDER", CHAT_CONFIG["llm_provider"])

    @property
    def openrouter_api_key(self) -> str:
        return _env("OPENROUTER_API_KEY", CHAT_CONFIG["openrouter_api_key"])

    @property
    def openrouter_model(self) -> str:
        return _env("LLM_MODEL", CHAT_CONFIG["openrouter_model"])

    @property
    def ollama_base_url(self) -> str:
        return _env("OLLAMA_URL", CHAT_CONFIG["ollama_base_url"])

    @property
    def ollama_llm_model(self) -> str:
        return _env("OLLAMA_LLM_MODEL", CHAT_CONFIG["ollama_llm_model"])

    @property
    def llm_temperature(self) -> float:
        return float(_env("LLM_TEMPERATURE", str(CHAT_CONFIG["llm_temperature"])))

    # --- Synthesis model ---
    @property
    def synth_model(self) -> str:
        return _env("SYNTH_MODEL", CHAT_CONFIG["synth_model"])

    @property
    def use_synth_custom(self) -> bool:
        return _env("USE_SYNTH_CUSTOM", "1" if CHAT_CONFIG["use_synth_custom"] else "0") == "1"

    # --- Embeddings ---
    @property
    def embed_provider(self) -> str:
        return _env("EMBED_PROVIDER", CHAT_CONFIG["embed_provider"])

    @property
    def openai_api_key(self) -> str:
        return _env("OPENAI_API_KEY", CHAT_CONFIG["openai_api_key"])

    @property
    def openai_embed_model(self) -> str:
        return _env("OPENAI_EMBED_MODEL", CHAT_CONFIG["openai_embed_model"])

    @property
    def ollama_embed_model(self) -> str:
        return _env("OLLAMA_EMBED_MODEL", CHAT_CONFIG["ollama_embed_model"])

    # --- RAG / agent ---
    @property
    def slm_mode(self) -> bool:
        return _env("SLM_MODE", "1" if CHAT_CONFIG["slm_mode"] else "0") == "1"

    @property
    def max_iterations(self) -> int:
        return int(_env("AGENT_MAX_ITER", str(CHAT_CONFIG["max_iterations"])))

    @property
    def use_reranker(self) -> bool:
        return _env("USE_RERANKER", "1" if CHAT_CONFIG["use_reranker"] else "0") == "1"

    @property
    def reranker_model(self) -> str:
        return _env("RERANKER_MODEL", CHAT_CONFIG["reranker_model"])

    @property
    def rerank_top_k(self) -> int:
        return int(_env("RERANK_TOP_K", str(CHAT_CONFIG["rerank_top_k"])))

    @property
    def rerank_keep(self) -> int:
        return int(_env("RERANK_KEEP", str(CHAT_CONFIG["rerank_keep"])))

    @property
    def top_k_per_ua(self) -> int:
        return int(_env("TOP_K_PER_UA", str(CHAT_CONFIG["top_k_per_ua"])))

    @property
    def top_k_global(self) -> int:
        return int(_env("TOP_K_GLOBAL", str(CHAT_CONFIG["top_k_global"])))

    # --- Vector store ---
    @property
    def qdrant_url(self) -> str:
        return _env("QDRANT_URL", CHAT_CONFIG["qdrant_url"])

    @property
    def qdrant_collection(self) -> str:
        return _env("QDRANT_COLLECTION", CHAT_CONFIG["qdrant_collection"])

    # --- Chunking ---
    @property
    def chunk_size(self) -> int:
        return int(_env("CHUNK_SIZE", str(CHAT_CONFIG["chunk_size"])))

    @property
    def chunk_overlap(self) -> int:
        return int(_env("CHUNK_OVERLAP", str(CHAT_CONFIG["chunk_overlap"])))


# Singleton — used by memory.py and throughout the chatbot
CFG = ChatCfg()

# Alias for backwards compatibility / convenience
CHAT = CFG

# Optional: merge from bundled `lib/activiity.config` if available
_ACTIVIITY_AVAILABLE = False
try:
    from lib.activiity.config import CFG as _ACFG, EVAL_CONFIG as _AEVAL
    _ACTIVIITY_AVAILABLE = True
except ImportError:
    pass


def activiity_available() -> bool:
    """Whether the bundled activiity RAG backend is installed and usable."""
    return _ACTIVIITY_AVAILABLE


def _lib_activiity_available() -> bool:
    """Check if bundled `lib/activiity/` is available."""
    try:
        import lib.activiity.config  # noqa: F401
        return True
    except ImportError:
        pass
    return False