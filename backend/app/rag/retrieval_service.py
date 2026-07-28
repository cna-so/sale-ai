from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient

from backend.app.core.config import Settings
from backend.app.core.exceptions import VectorStoreError
from backend.app.models.domain import RetrievedDocument
from backend.app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        qdrant: AsyncQdrantClient,
    ) -> None:
        self._settings = settings
        self._embedding = embedding_service
        self._qdrant = qdrant

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        collection: str | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        """Embed *query* and return the top-k most similar chunks.

        Chunks whose cosine similarity is below *score_threshold* (defaults to
        ``settings.rag_score_threshold``) are discarded so the LLM never
        receives irrelevant context.
        """
        top_k = top_k or self._settings.rag_top_k
        collection = collection or self._settings.qdrant_collection
        threshold = score_threshold if score_threshold is not None else self._settings.rag_score_threshold

        try:
            query_vector = await self._embedding.embed_one(query)
            results = await self._qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
                score_threshold=threshold,
            )
        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            raise VectorStoreError(f"Retrieval failed: {exc}") from exc

        docs: list[RetrievedDocument] = []
        for hit in results:
            payload = hit.payload or {}
            docs.append(
                RetrievedDocument(
                    content=payload.get("content", ""),
                    source=payload.get("source", ""),
                    title=payload.get("title", ""),
                    chunk_index=payload.get("chunk_index", 0),
                    document_id=payload.get("document_id", ""),
                    score=float(hit.score),
                )
            )
        return docs
