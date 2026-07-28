from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import Settings
from backend.app.core.exceptions import EmbeddingError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Maximum number of texts sent to the embeddings API in a single request.
# Most providers cap at ~8192 tokens per request; 32 texts is a safe default.
_MAX_BATCH = 32

_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)


class EmbeddingService:
    """Thin async wrapper around OpenRouter's embeddings endpoint.

    A single :class:`httpx.AsyncClient` is reused across calls so the
    connection pool is shared. Use :meth:`aclose` (or FastAPI lifespan) to
    shut it down cleanly.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        # Dimension comes from settings so a model switch needs only one change.
        self.dimension: int = settings.embedding_dimension
        self._client = httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers)

    async def aclose(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Send exactly one batch (len <= _MAX_BATCH) to the embeddings API."""
        payload = {
            "model": self._settings.openrouter_embedding_model,
            "input": texts,
        }
        try:
            resp = await self._client.post(
                f"{self._base_url}/embeddings",
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Embedding HTTP error %s: %s", e.response.status_code, e.response.text)
            raise EmbeddingError(f"Embedding request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EmbeddingError(f"Embedding connection error: {e}") from e

        data = resp.json()
        try:
            return [item["embedding"] for item in data["data"]]
        except (KeyError, TypeError) as e:
            raise EmbeddingError("Unexpected embedding response format.") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors for each input text.

        Automatically splits *texts* into batches of at most ``_MAX_BATCH``
        entries to stay within provider request size limits.
        """
        if not self._settings.is_openrouter_configured:
            raise EmbeddingError("OpenRouter API key not configured.")
        if not texts:
            return []

        results: list[list[float]] = []
        for i in range(0, len(texts), _MAX_BATCH):
            batch = texts[i : i + _MAX_BATCH]
            results.extend(await self._embed_batch(batch))
        return results

    async def embed_one(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]
