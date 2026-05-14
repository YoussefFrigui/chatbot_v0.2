"""LLM / Embedding provider factory.

Same env knobs as the naive baseline so target swaps are apples-to-apples.
"""
from __future__ import annotations

from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding

from lib.activiity.config import CFG


def build_llm() -> LLM:
    if CFG.llm_provider == "openrouter":
        from llama_index.llms.openrouter import OpenRouter
        return OpenRouter(
            api_key=CFG.openrouter_api_key or None,
            model=CFG.openrouter_model,
            temperature=CFG.llm_temperature,
            max_tokens=1024,
        )
    if CFG.llm_provider == "ollama":
        from llama_index.llms.ollama import Ollama
        return Ollama(
            base_url=CFG.ollama_base_url,
            model=CFG.ollama_llm_model,
            temperature=CFG.llm_temperature,
            request_timeout=120.0,
        )
    raise ValueError(f"Unknown llm_provider: {CFG.llm_provider}")


def build_synth_llm() -> LLM:
    if CFG.use_synth_custom:
        from llama_index.llms.openrouter import OpenRouter
        return OpenRouter(
            api_key=CFG.openrouter_api_key or None,
            model=CFG.synth_model,
            temperature=CFG.llm_temperature,
            max_tokens=512,
        )
    return build_llm()


def build_embed() -> BaseEmbedding:
    if CFG.embed_provider == "openai":
        from llama_index.embeddings.openai import OpenAIEmbedding
        return OpenAIEmbedding(
            api_key=CFG.openai_api_key or None,
            model=CFG.openai_embed_model,
        )
    if CFG.embed_provider == "ollama":
        from llama_index.embeddings.ollama import OllamaEmbedding
        return OllamaEmbedding(
            base_url=CFG.ollama_base_url, model_name=CFG.ollama_embed_model,
        )
    raise ValueError(f"Unknown embed_provider: {CFG.embed_provider}")