from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
)

from backend.app.core.exceptions import VectorStoreError
from backend.app.services.embedding_service import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


async def ensure_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    vector_size: int = EMBEDDING_DIMENSION,
) -> None:
    """Create the Qdrant collection if it does not already exist."""
    try:
        existing = await client.get_collections()
        names = [c.name for c in existing.collections]
        if collection_name not in names:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s' (dim=%d)", collection_name, vector_size)
        else:
            logger.debug("Collection '%s' already exists.", collection_name)
    except Exception as exc:
        raise VectorStoreError(f"Failed to ensure collection '{collection_name}': {exc}") from exc
