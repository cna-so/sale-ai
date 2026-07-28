from __future__ import annotations

import logging

import httpx

from backend.app.core.config import Settings
from backend.app.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 1536  # text-embedding-3-small default


class EmbeddingService:
    """Thin async wrapper around OpenRouter's embeddings endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors for each input text."""
        if not self._settings.is_openrouter_configured:
            raise EmbeddingError("OpenRouter API key not configured.")
        if not texts:
            return []

        payload = {
            "model": self._settings.openrouter_embedding_model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/embeddings",
                    headers=self._headers,
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

    async def embed_one(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]
