#!/usr/bin/env python3
"""
Index all seed documents in data/documents/ into Qdrant.

Usage (from repo root):
    python -m backend.scripts.index_documents
    # or inside Docker:
    docker compose exec api python -m backend.scripts.index_documents
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.rag.indexing_service import IndexingService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.vectorstore.qdrant_client import get_qdrant_client

DOCS_DIR = Path("data/documents")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("index_documents")

    if not settings.is_openrouter_configured:
        logger.error("OPENROUTER_API_KEY is not set. Cannot generate embeddings.")
        return

    embedding = EmbeddingService(settings)
    qdrant = get_qdrant_client(settings)
    service = IndexingService(settings, embedding, qdrant)

    md_files = list(DOCS_DIR.glob("*.md")) + list(DOCS_DIR.glob("*.txt")) + list(DOCS_DIR.glob("*.pdf"))
    if not md_files:
        logger.warning("No documents found in %s", DOCS_DIR)
        return

    for doc_path in sorted(md_files):
        try:
            result = await service.index_file(doc_path)
            logger.info(
                "Indexed '%s' -> %d chunks (doc_id=%s)",
                doc_path.name,
                result["chunks_indexed"],
                result["document_id"],
            )
        except Exception as exc:
            logger.error("Failed to index '%s': %s", doc_path.name, exc)

    logger.info("Done indexing all documents.")


if __name__ == "__main__":
    asyncio.run(main())
