"""OpenAI-compatible /v1/chat/completions router for LibreChat integration.

LibreChat (and any OpenAI-compatible client) sends:
  POST /v1/chat/completions
  { model, messages, stream, ... }

This adapter:
  1. Extracts the last user message plus an optional conversation_id.
  2. Calls the existing ShoppingAgent.
  3. Returns a standard OpenAI chat completion (or SSE stream).
  4. Flattens product widgets into chat-safe markdown/plain text so LibreChat
     can render card-like shopping results without custom widget support.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import AsyncIterator
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.api.dependencies import get_shopping_agent
from backend.app.core.config import Settings, get_settings
from backend.app.utils.ids import new_id
from backend.app.utils.product_markdown import build_shopping_chat_content

logger = logging.getLogger(__name__)
router = APIRouter(tags=["openai-compat"])

MODEL_ID = "sale-ai"


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class OAIImageURL(BaseModel):
    url: str


class OAIContentPart(BaseModel):
    type: str
    text: str | None = None
    image_url: OAIImageURL | str | None = None


class OAIMessage(BaseModel):
    role: str
    content: str | list[OAIContentPart] | None = None


class OAIChatRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[OAIMessage] = Field(default_factory=list)
    stream: bool = False
    # LibreChat sometimes passes conversation_id as a top-level extra field
    conversation_id: str | None = Field(default=None, alias="conversation_id")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ---------------------------------------------------------------------------
# Conversation-id / multimodal helpers
# ---------------------------------------------------------------------------

def _extract_conversation_id(req: OAIChatRequest) -> str | None:
    """Try to find a reusable conversation_id from the request."""
    if req.conversation_id:
        return req.conversation_id

    for msg in req.messages:
        if msg.role == "system" and msg.content:
            import re
            m = re.search(r"\[conversation_id:([\w-]+)\]", msg.content)
            if m:
                return m.group(1)

    return None


def _extract_image_data(url: str) -> tuple[bytes, str] | None:
    """Decode OpenAI data URLs or a LibreChat image mounted into this container."""
    if url.startswith("data:image/"):
        header, _, encoded = url.partition(",")
        if not encoded or ";base64" not in header:
            return None
        content_type = header.removeprefix("data:").split(";", 1)[0]
        try:
            return base64.b64decode(encoded, validate=True), content_type
        except ValueError:
            return None

    parsed = urlparse(url)
    if parsed.path.startswith("/images/"):
        from pathlib import Path

        image_path = Path("/librechat_uploads") / Path(parsed.path).name
        if image_path.is_file():
            content_type = "image/" + (image_path.suffix.removeprefix(".") or "jpeg")
            return image_path.read_bytes(), content_type
    return None


def _extract_user_input(req: OAIChatRequest) -> tuple[str, bytes | None, str | None]:
    """Return the last user text and an optional OpenAI-compatible image."""
    for msg in reversed(req.messages):
        if msg.role != "user" or not msg.content:
            continue
        if isinstance(msg.content, str):
            return msg.content, None, None
        text_parts: list[str] = []
        for part in msg.content:
            if part.type == "text" and part.text:
                text_parts.append(part.text)
            if part.type == "image_url" and part.image_url:
                url = part.image_url.url if isinstance(part.image_url, OAIImageURL) else part.image_url
                image = _extract_image_data(url)
                if image:
                    return "\n".join(text_parts), image[0], image[1]
        return "\n".join(text_parts), None, None
    return "", None, None


def _resolve_language(state: dict) -> str:
    intent = state.get("intent")
    if intent is not None and getattr(intent, "detected_language", None):
        return intent.detected_language
    locale = state.get("locale") or ""
    return "fa" if locale.startswith("fa") else "en"


def _build_assistant_content(state: dict, settings: Settings) -> str:
    """Flatten shopping state into OpenAI-spec assistant text."""
    intent = state.get("intent")
    intent_label = intent.intent if intent is not None else None
    # OpenAI clients cannot render custom widgets; widgets mode still flattens.
    render_mode = "markdown" if settings.librechat_render_mode == "widgets" else settings.librechat_render_mode
    return build_shopping_chat_content(
        answer=state.get("answer", ""),
        products=state.get("products", []),
        widgets=state.get("widgets", []),
        reasons=state.get("recommendation_reasons", []),
        language=_resolve_language(state),
        render_mode=render_mode,
        include_image=settings.librechat_include_product_images,
        intent=intent_label,
    )


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse_chunk(delta: str, request_id: str, finish: bool = False) -> str:
    chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [{
            "index": 0,
            "delta": {} if finish else {"role": "assistant", "content": delta},
            "finish_reason": "stop" if finish else None,
        }],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


async def _stream_response(content: str, request_id: str) -> AsyncIterator[str]:
    """Simulate token streaming by yielding ~word-sized chunks."""
    words = content.split(" ")
    for i, word in enumerate(words):
        chunk_text = word + (" " if i < len(words) - 1 else "")
        yield _sse_chunk(chunk_text, request_id)
        await asyncio.sleep(0)
    yield _sse_chunk("", request_id, finish=True)
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/v1/models")
async def list_models():
    """Model listing endpoint — LibreChat probes this on startup."""
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": 1700000000,
                "owned_by": "sale-ai",
                "permission": [],
                "root": MODEL_ID,
                "parent": None,
            }
        ],
    }


@router.post("/v1/chat/completions")
async def chat_completions(
    req: OAIChatRequest,
    agent: ShoppingAgent = Depends(get_shopping_agent),
    settings: Settings = Depends(get_settings),
):
    """OpenAI-compatible chat completions endpoint."""
    user_message, image_data, image_content_type = _extract_user_input(req)
    conversation_id = _extract_conversation_id(req) or new_id()
    request_id = f"chatcmpl-{new_id()}"

    logger.info(
        "OAI-compat request | conv=%s | stream=%s | msg=%.80s",
        conversation_id, req.stream, user_message,
    )

    state = await agent.run(
        conversation_id=conversation_id,
        user_message=user_message,
        image_data=image_data,
        image_content_type=image_content_type,
    )

    content = _build_assistant_content(state, settings)

    if req.stream:
        return StreamingResponse(
            _stream_response(content, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Spec-compliant body only — no custom top-level shopping fields.
    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content,
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
