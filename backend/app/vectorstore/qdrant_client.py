from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from backend.app.core.config import Settings
from backend.app.core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None


def get_qdrant_client(settings: Settings) -> AsyncQdrantClient:
    """Return a module-level singleton AsyncQdrantClient."""
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30,
        )
        logger.info("Qdrant client created -> %s:%s", settings.qdrant_host, settings.qdrant_port)
    return _client


async def check_qdrant_health(client: AsyncQdrantClient) -> bool:
    """Ping Qdrant and return True if reachable."""
    try:
        await client.get_collections()
        return True
    except Exception as exc:
        logger.warning("Qdrant health check failed: %s", exc)
        return False
