"""Standalone ingestion CLI.

Usage:
    cd chatbot_v0.2
    python -m lib.activiity.ingest.cli

Options:
    --force     Drop existing collection and re-embed everything
    --dry-run   Show what would be ingested without uploading to Qdrant

Examples:
    # First time (creates collection, loads data, embeds)
    python -m lib.activiity.ingest.cli

    # Re-ingest (force overwrite)
    python -m lib.activiity.ingest.cli --force
"""
from __future__ import annotations
import argparse
import json
import os

from lib.activiity.ingest.pipeline import build_index


def main():
    ap = argparse.ArgumentParser(
        description="Ingest the Activiity knowledge base into Qdrant."
    )
    ap.add_argument(
        "--force", action="store_true",
        help="Drop existing collection and re-embed everything",
    )
    args = ap.parse_args()

    # Ensure Qdrant is reachable
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    print(f"[ingest] QDRANT_URL={qdrant_url}")

    info = build_index(force=args.force)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()