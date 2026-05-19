"""Env-driven config for the Agentic RAG (matches naive baseline knobs)."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# =============================================================================
# CODE-BASED CONFIG — Edit these values directly for experiments
# =============================================================================
EVAL_CONFIG = {
    "router_model": "qwen/qwen3-14b",
    "synth_model": "qwen/qwen3-8b",
    "slm_mode": True,
    "max_iterations": 2,
    "use_reranker": False,
    "agent_timeout_s": 180,
}
# =============================================================================
DATA_DIR = Path(os.getenv("ACTIVIITY_DATA_DIR", str(ROOT / "data")))


class Cfg:
    """Config that reads env vars at runtime (not at import time)."""

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "openrouter")

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def openrouter_model(self) -> str:
        if "router_model" in EVAL_CONFIG:
            return EVAL_CONFIG["router_model"]
        return os.getenv("LLM_MODEL", "qwen/qwen3-14b")

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_URL", "http://localhost:11434")

    @property
    def ollama_llm_model(self) -> str:
        return os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:14b-instruct")

    @property
    def llm_temperature(self) -> float:
        return float(os.getenv("LLM_TEMPERATURE", "0.2"))

    @property
    def embed_provider(self) -> str:
        return os.getenv("EMBED_PROVIDER", "ollama")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def openai_embed_model(self) -> str:
        return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    @property
    def ollama_embed_model(self) -> str:
        return os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

    @property
    def qdrant_url(self) -> str:
        return os.getenv("QDRANT_URL", "http://localhost:6333")

    @property
    def qdrant_collection_base(self) -> str:
        return os.getenv("QDRANT_COLLECTION", "activiity_kb")

    @property
    def chunk_size(self) -> int:
        return int(os.getenv("CHUNK_SIZE", "512"))

    @property
    def chunk_overlap(self) -> int:
        return int(os.getenv("CHUNK_OVERLAP", "64"))

    @property
    def top_k_per_ua(self) -> int:
        return int(os.getenv("TOP_K_PER_UA", "5"))

    @property
    def top_k_global(self) -> int:
        return int(os.getenv("TOP_K_GLOBAL", "8"))

    @property
    def max_iterations(self) -> int:
        if "max_iterations" in EVAL_CONFIG:
            return EVAL_CONFIG["max_iterations"]
        return int(os.getenv("AGENT_MAX_ITER", "2"))

    @property
    def agent_timeout_s(self) -> int:
        if "agent_timeout_s" in EVAL_CONFIG:
            return int(EVAL_CONFIG["agent_timeout_s"])
        return int(os.getenv("AGENT_TIMEOUT_S", "180"))

    @property
    def use_reranker(self) -> bool:
        if "use_reranker" in EVAL_CONFIG:
            return EVAL_CONFIG["use_reranker"]
        return os.getenv("USE_RERANKER", "1") == "1"

    @property
    def reranker_model(self) -> str:
        return os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

    @property
    def rerank_top_k(self) -> int:
        return int(os.getenv("RERANK_TOP_K", "20"))

    @property
    def rerank_keep(self) -> int:
        return int(os.getenv("RERANK_KEEP", "5"))

    @property
    def use_synth_custom(self) -> bool:
        if "synth_model" in EVAL_CONFIG and EVAL_CONFIG["synth_model"]:
            return True
        return os.getenv("USE_SYNTH_CUSTOM", "0") == "1"

    @property
    def synth_model(self) -> str:
        if "synth_model" in EVAL_CONFIG and EVAL_CONFIG["synth_model"]:
            return EVAL_CONFIG["synth_model"]
        return os.getenv("SYNTH_MODEL", "qwen/qwen3-14b")

    @property
    def haiku_model(self) -> str:
        return os.getenv("HAIKU_MODEL", "anthropic/claude-haiku-4-5")

    @property
    def use_structure_splitter(self) -> bool:
        return os.getenv("USE_STRUCTURE_SPLITTER", "0") == "1"

    @property
    def slm_mode(self) -> bool:
        if "slm_mode" in EVAL_CONFIG:
            return EVAL_CONFIG["slm_mode"]
        return os.getenv("SLM_MODE", "0") == "1"

    @property
    def slm_max_tokens(self) -> int:
        return int(os.getenv("SLM_MAX_TOKENS", "512"))

    @property
    def slm_temperature(self) -> float:
        return float(os.getenv("SLM_TEMPERATURE", "0.1"))


CFG = Cfg()
UA_IDS = [f"UA-{i}" for i in range(1, 11)]


def collection_name(embed_model: str) -> str:
    safe = embed_model.replace("/", "_")
    suffix = "__structure" if CFG.use_structure_splitter else ""
    return f"{CFG.qdrant_collection_base}__{safe}{suffix}"