"""Standalone ingestion pipeline for Qdrant.

Ingest the knowledge base from chatbot_v0.2/data/ into Qdrant.
No parent repo needed — all deps are in lib/.
"""
from __future__ import annotations
from pathlib import Path

from llama_index.core import Settings as LISettings, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models as qm

from lib.activiity.config import CFG, collection_name
from lib.activiity.providers.factory import build_embed
from lib.baseline.loader import load_corpus


def _bundle_data_dir() -> Path:
    """Find the data directory inside the bundled chatbot_v0.2 tree."""
    # lib/activiity/ingest/pipeline.py → parents[3] = chatbot_v0.2/
    configured = Path(__file__).resolve().parents[3]
    bundle = configured / "data"
    if bundle.exists():
        return bundle
    return bundle


def ensure_collection(client: QdrantClient, name: str, dim: int):
    """Create the collection + payload index on ua_id if missing."""
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )
        client.create_payload_index(
            name, field_name="ua_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )


def build_index(force: bool = False) -> dict:
    """Build the Qdrant index. Idempotent unless force=True."""
    embed = build_embed()
    LISettings.embed_model = embed

    dim = len(embed.get_text_embedding("ping"))
    coll = collection_name(
        CFG.openai_embed_model if CFG.embed_provider == "openai"
        else CFG.ollama_embed_model
    )

    client = QdrantClient(url=CFG.qdrant_url, timeout=60)

    if force and client.collection_exists(coll):
        client.delete_collection(coll)

    ensure_collection(client, coll, dim)

    info = client.get_collection(coll)
    if info.points_count and not force:
        print(f"[ingest] collection {coll!r} already has "
              f"{info.points_count} points — skipping (force=False)")
        return {"collection": coll, "points": info.points_count, "skipped": True}

    vstore = QdrantVectorStore(client=client, collection_name=coll)

    splitter = SentenceSplitter(
        chunk_size=CFG.chunk_size, chunk_overlap=CFG.chunk_overlap,
    )

    pipeline = IngestionPipeline(
        transformations=[splitter, embed],
        vector_store=vstore,
    )

    DATA_DIR = _bundle_data_dir()
    docs = load_corpus(DATA_DIR)
    if not docs:
        raise RuntimeError(f"no documents found under {DATA_DIR} — "
                           f"copy data/UA-* folders into chatbot_v0.2/data/ first")

    print(f"[ingest] loading {len(docs)} documents from {DATA_DIR}")
    nodes = pipeline.run(documents=docs, show_progress=True)
    info = client.get_collection(coll)
    return {
        "collection": coll,
        "embed_model": embed.model_name if hasattr(embed, "model_name") else str(embed),
        "documents": len(docs),
        "nodes": len(nodes),
        "points": info.points_count,
        "skipped": False,
    }


def open_index() -> tuple:
    """Open the existing Qdrant collection as a LlamaIndex VectorStoreIndex."""
    embed = build_embed()
    LISettings.embed_model = embed

    coll = collection_name(
        CFG.openai_embed_model if CFG.embed_provider == "openai"
        else CFG.ollama_embed_model
    )

    client = QdrantClient(url=CFG.qdrant_url, timeout=60)
    if not client.collection_exists(coll):
        raise RuntimeError(
            f"Qdrant collection {coll!r} not found. "
            "Run ingestion first: python -m lib.activiity.ingest.cli"
        )

    vstore = QdrantVectorStore(client=client, collection_name=coll)
    index = VectorStoreIndex.from_vector_store(vstore)
    return index, client, coll