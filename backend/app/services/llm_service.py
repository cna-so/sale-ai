from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import Settings
from backend.app.core.exceptions import LLMError

logger = logging.getLogger(__name__)

# Separate connect and read timeouts so slow-streaming responses don't hit the
# connect timeout, and hung connections don't block forever.
_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)


class LLMService:
    """Thin async wrapper around OpenRouter's OpenAI-compatible chat endpoint.

    A single :class:`httpx.AsyncClient` is shared across all calls so the
    underlying TCP connection pool is reused (HTTP/2 multiplexing).
    Call :meth:`aclose` (or use the FastAPI lifespan) to shut it down cleanly.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.app_env and "https://github.com/cna-so/sale-ai" or "",
            "X-Title": "AI Shopping Assistant",
        }
        # Long-lived client — do NOT create a new client per request.
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
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send chat messages and return the assistant content string."""
        if not self._settings.is_openrouter_configured:
            raise LLMError("OpenRouter API key not configured.")

        payload: dict[str, Any] = {
            "model": model or self._settings.openrouter_chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            resp = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error %s: %s", e.response.status_code, e.response.text)
            raise LLMError(f"LLM request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("LLM request error: %s", e)
            raise LLMError(f"LLM connection error: {e}") from e

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error("Unexpected LLM response shape: %s", data)
            raise LLMError("Unexpected response format from LLM.") from e

    async def chat_with_image(
        self,
        text_prompt: str,
        image_base64: str,
        content_type: str,
        model: str | None = None,
        max_tokens: int = 512,
    ) -> str:
        """Send a vision request with base64 image and return content string."""
        if not self._settings.is_openrouter_configured:
            raise LLMError("OpenRouter API key not configured.")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{content_type};base64,{image_base64}"},
                    },
                ],
            }
        ]
        return await self.chat(
            messages=messages,
            model=model or self._settings.openrouter_vision_model,
            max_tokens=max_tokens,
        )
