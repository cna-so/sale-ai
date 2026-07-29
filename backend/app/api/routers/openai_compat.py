"""OpenAI-compatible /v1/chat/completions router for LibreChat integration.

LibreChat (and any OpenAI-compatible client) sends:
  POST /v1/chat/completions
  { model, messages, stream, ... }

This adapter:
  1. Extracts the last user message plus an optional conversation_id stored
     in the system prompt (LibreChat passes it via a hidden system message).
  2. Calls the existing ShoppingAgent with the full message history context.
  3. Returns a standard OpenAI chat completion (or SSE stream).
  4. Serialises rich widgets (comparison tables, product cards) as Markdown
     so LibreChat renders them natively.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.api.dependencies import get_shopping_agent
from backend.app.schemas.chat import DebugInfo
from backend.app.utils.ids import new_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["openai-compat"])

MODEL_ID = "sale-ai"


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class OAIMessage(BaseModel):
    role: str
    content: str | None = None


class OAIChatRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[OAIMessage] = Field(default_factory=list)
    stream: bool = False
    # LibreChat sometimes passes conversation_id as a top-level extra field
    conversation_id: str | None = Field(default=None, alias="conversation_id")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ---------------------------------------------------------------------------
# Widget → Markdown serialiser
# ---------------------------------------------------------------------------

def _widget_to_markdown(widget: dict) -> str:
    """Convert a sale-ai widget payload to a Markdown string."""
    wtype = widget.get("type", "")
    data = widget.get("data", {})

    if wtype == "comparison_table":
        title = data.get("title", "")
        columns: list[str] = data.get("columns", [])
        rows: list[list] = data.get("rows", [])
        if not columns:
            return ""
        header = "| " + " | ".join(str(c) for c in columns) + " |"
        sep = "|" + "|".join([" --- "] * len(columns)) + "|"
        body_lines = [
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in rows
        ]
        parts = []
        if title:
            parts.append(f"**{title}**")
        parts += [header, sep] + body_lines
        return "\n".join(parts)

    if wtype == "product_card":
        name = data.get("name", "")
        price = data.get("price", "")
        rating = data.get("rating", "")
        url = data.get("url", "")
        lines = [f"**{name}**"]
        if price:
            lines.append(f"- قیمت: {price}")
        if rating:
            lines.append(f"- امتیاز: {rating}")
        if url:
            lines.append(f"- [مشاهده محصول]({url})")
        return "\n".join(lines)

    if wtype == "text":
        return data.get("content", "")

    # Generic fallback: dump as JSON code block
    return f"```json\n{json.dumps(widget, ensure_ascii=False, indent=2)}\n```"


def _build_content(answer: str, widgets: list, products: list) -> str:
    """Combine agent answer + widgets + products into a single Markdown string."""
    parts = [answer] if answer else []

    for w in widgets or []:
        md = _widget_to_markdown(w if isinstance(w, dict) else w.model_dump())
        if md:
            parts.append(md)

    for p in products or []:
        p_dict = p if isinstance(p, dict) else p.model_dump()
        name = p_dict.get("name", "")
        price = p_dict.get("price", "")
        url = p_dict.get("url", "")
        line = f"- **{name}**" + (f" — {price}" if price else "") + (f" ([link]({url}))" if url else "")
        parts.append(line)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Conversation-id extraction helpers
# ---------------------------------------------------------------------------

def _extract_conversation_id(req: OAIChatRequest) -> str | None:
    """Try to find a reusable conversation_id from the request.

    LibreChat does not natively forward a conversation_id in the OAI body,
    but we check three places:
    1. An explicit `conversation_id` field (custom LibreChat param).
    2. A system message containing `[conversation_id:<id>]` marker.
    3. Generate a fresh one so the whole request stays in one thread.
    """
    if req.conversation_id:
        return req.conversation_id

    for msg in req.messages:
        if msg.role == "system" and msg.content:
            import re
            m = re.search(r"\[conversation_id:([\w-]+)\]", msg.content)
            if m:
                return m.group(1)

    return None


def _extract_user_message(req: OAIChatRequest) -> str:
    """Return the last user message content."""
    for msg in reversed(req.messages):
        if msg.role == "user" and msg.content:
            return msg.content
    return ""


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
        await asyncio.sleep(0)  # yield control; replace with real streaming when LLM supports it
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
):
    """OpenAI-compatible chat completions endpoint."""
    user_message = _extract_user_message(req)
    conversation_id = _extract_conversation_id(req) or new_id()
    request_id = f"chatcmpl-{new_id()}"

    logger.info(
        "OAI-compat request | conv=%s | stream=%s | msg=%.80s",
        conversation_id, req.stream, user_message,
    )

    # Run the LangGraph shopping agent
    state = await agent.run(
        conversation_id=conversation_id,
        user_message=user_message,
    )

    content = _build_content(
        answer=state.get("answer", ""),
        widgets=state.get("widgets", []),
        products=state.get("products", []),
    )

    if req.stream:
        return StreamingResponse(
            _stream_response(content, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

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
