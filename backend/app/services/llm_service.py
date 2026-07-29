from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.core.exceptions import LLMError

logger = logging.getLogger(__name__)


def _message_text(message: dict[str, Any]) -> str:
    """Normalize OpenAI/OpenRouter message content to a plain string."""
    content = message.get("content")
    if content is None:
        # Some providers put a blocked/refusal reason here instead of content.
        refusal = message.get("refusal")
        if refusal:
            return str(refusal).strip()
        return ""
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") in {None, "text"} and part.get("text"):
                    text_parts.append(str(part["text"]))
                elif part.get("text"):
                    text_parts.append(str(part["text"]))
        return "\n".join(p for p in text_parts if p).strip()
    return str(content).strip()


class LLMService:
    """Thin async wrapper around OpenRouter's OpenAI-compatible chat endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/cna-so/sale-ai",
            "X-Title": "AI Shopping Assistant",
        }

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

        resolved_model = model or self._settings.openrouter_chat_model
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("LLM HTTP error %s: %s", e.response.status_code, e.response.text[:500])
                raise LLMError(f"LLM request failed: {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error("LLM request error: %s", e)
                raise LLMError(f"LLM connection error: {e}") from e

        data = resp.json()
        try:
            choice = data["choices"][0]
            message = choice.get("message") or {}
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as e:
            logger.error("Unexpected LLM response shape: %s", data)
            raise LLMError("Unexpected response format from LLM.") from e

        content = _message_text(message)
        logger.info(
            "LLM ok model=%s finish=%s content_len=%d",
            resolved_model,
            finish_reason,
            len(content),
        )
        if not content:
            logger.error(
                "LLM returned blank content model=%s finish=%s keys=%s",
                resolved_model,
                finish_reason,
                list(message.keys()),
            )
            raise LLMError("LLM returned empty content.")
        return content

    async def chat_with_image(
        self,
        text_prompt: str,
        image_base64: str,
        content_type: str,
        model: str | None = None,
        max_tokens: int = 512,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Send a vision request with base64 image and return content string.

        Note: do NOT force json_object by default — several OpenRouter vision
        models return empty content when json_object is combined with images.
        """
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
            temperature=temperature,
            response_format=response_format,
        )
