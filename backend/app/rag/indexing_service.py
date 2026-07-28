from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import PointStruct

from backend.app.core.config import Settings
from backend.app.core.exceptions import VectorStoreError
from backend.app.rag.chunking import TextChunk, chunk_text
from backend.app.rag.document_loader import load_document
from backend.app.services.embedding_service import EmbeddingService
from backend.app.utils.ids import new_id
from backend.app.vectorstore.collections import ensure_collection

logger = logging.getLogger(__name__)

_BATCH_SIZE = 32


def _deterministic_point_id(document_id: str, chunk_index: int) -> str:
    """Derive a stable UUID-shaped string from (document_id, chunk_index).

    Using a deterministic ID means re-indexing the same file upserts
    (overwrites) existing vectors instead of creating duplicates.
    """
    raw = f"{document_id}:{chunk_index}"
    digest = hashlib.md5(raw.encode()).hexdigest()
    # Format as UUID for Qdrant compatibility: 8-4-4-4-12
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


class IndexingService:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        qdrant: AsyncQdrantClient,
    ) -> None:
        self._settings = settings
        self._embedding = embedding_service
        self._qdrant = qdrant

    async def index_file(
        self,
        file_path: str | Path,
        collection: str | None = None,
        document_id: str | None = None,
    ) -> dict:
        """Load, chunk, embed and upsert a file into Qdrant.

        Re-indexing the same file is safe: deterministic point IDs ensure that
        ``upsert`` overwrites existing vectors rather than creating duplicates.
        """
        path = Path(file_path)
        collection = collection or self._settings.qdrant_collection
        doc_id = document_id or new_id()
        title = path.stem.replace("_", " ").replace("-", " ").title()

        logger.info("Indexing '%s' -> collection='%s' doc_id='%s'", path.name, collection, doc_id)

        text = load_document(path)
        chunks = chunk_text(
            text=text,
            source=path.name,
            document_id=doc_id,
            title=title,
            chunk_size=self._settings.rag_chunk_size,
            chunk_overlap=self._settings.rag_chunk_overlap,
        )

        if not chunks:
            logger.warning("No chunks produced from '%s'", path.name)
            return {"chunks_indexed": 0, "document_id": doc_id, "collection": collection}

        await ensure_collection(self._qdrant, collection)

        total_upserted = 0
        for i in range(0, len(chunks), _BATCH_SIZE):
            batch: list[TextChunk] = chunks[i : i + _BATCH_SIZE]
            texts = [c.content for c in batch]
            vectors = await self._embedding.embed(texts)

            points = [
                PointStruct(
                    id=_deterministic_point_id(chunk.document_id, chunk.chunk_index),
                    vector=vec,
                    payload={
                        "content": chunk.content,
                        "source": chunk.source,
                        "title": chunk.title,
                        "chunk_index": chunk.chunk_index,
                        "document_id": chunk.document_id,
                    },
                )
                for chunk, vec in zip(batch, vectors)
            ]
            await self._qdrant.upsert(collection_name=collection, points=points)
            total_upserted += len(points)

        logger.info("Indexed %d chunks from '%s'", total_upserted, path.name)
        return {
            "chunks_indexed": total_upserted,
            "document_id": doc_id,
            "collection": collection,
        }
