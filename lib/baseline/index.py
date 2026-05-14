"""Build or load the single flat vector index over all UA buckets."""
from __future__ import annotations
from pathlib import Path

from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    Settings as LISettings,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter

from lib.baseline.config import CFG, DATA_DIR, PERSIST_DIR
from lib.baseline.loader import load_corpus
from lib.baseline.providers import build_embed


def _attach_providers_to_global_settings():
    # LLM not needed anymore (direct API calls in service.py)
    LISettings.embed_model = build_embed()
    LISettings.node_parser = SentenceSplitter(
        chunk_size=CFG.chunk_size, chunk_overlap=CFG.chunk_overlap,
    )


def build_index(data_dir: Path = DATA_DIR, persist_dir: Path = PERSIST_DIR,
                show_progress: bool = True) -> VectorStoreIndex:
    _attach_providers_to_global_settings()
    persist_dir.mkdir(parents=True, exist_ok=True)

    docs = load_corpus(data_dir)
    if not docs:
        raise RuntimeError(f"No documents found under {data_dir}")

    index = VectorStoreIndex.from_documents(docs, show_progress=show_progress)
    index.storage_context.persist(persist_dir=str(persist_dir))
    return index


def load_index(persist_dir: Path = PERSIST_DIR) -> VectorStoreIndex:
    _attach_providers_to_global_settings()
    storage = StorageContext.from_defaults(persist_dir=str(persist_dir))
    return load_index_from_storage(storage)


def build_or_load(data_dir: Path = DATA_DIR,
                  persist_dir: Path = PERSIST_DIR) -> VectorStoreIndex:
    if (persist_dir / "docstore.json").exists():
        return load_index(persist_dir)
    return build_index(data_dir, persist_dir)