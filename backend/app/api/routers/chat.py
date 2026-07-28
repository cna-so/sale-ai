from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.api.dependencies import get_shopping_agent
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import FileSizeExceededError, UnsupportedFileTypeError
from backend.app.schemas.chat import ChatRequest, ChatResponse, DebugInfo
from backend.app.utils.files import validate_extension
from backend.app.utils.ids import new_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: ShoppingAgent = Depends(get_shopping_agent),
    settings: Settings = Depends(get_settings),
):
    conversation_id = request.conversation_id or new_id()
    state = await agent.run(
        conversation_id=conversation_id,
        user_message=request.message,
        locale=request.metadata.locale,
        currency=request.metadata.currency,
    )

    intent = state.get("intent")
    return ChatResponse(
        conversation_id=conversation_id,
        message_id=state.get("assistant_message_id") or new_id(),
        answer=state.get("answer", ""),
        intent=intent.intent if intent else "general_chat",
        products=state.get("products", []),
        widgets=state.get("widgets", []),
        sources=state.get("sources", []),
        debug=DebugInfo(
            used_rag=state.get("used_rag", False),
            used_product_search=state.get("used_product_search", False),
            used_image_analysis=state.get("used_image_analysis", False),
            intent_confidence=intent.confidence if intent else 1.0,
            detected_language=intent.detected_language if intent else "fa",
        ),
    )


@router.post("/chat/image", response_model=ChatResponse)
async def chat_image(
    image: UploadFile = File(..., description="Product image"),
    message: str | None = Form(default=None),
    conversation_id: str | None = Form(default=None),
    locale: str = Form(default="fa-IR"),
    agent: ShoppingAgent = Depends(get_shopping_agent),
    settings: Settings = Depends(get_settings),
):
    # Validate file type
    try:
        validate_extension(image.filename or "")
    except ValueError:
        allowed_image_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if image.content_type not in allowed_image_types:
            raise UnsupportedFileTypeError(image.content_type or "unknown")

    image_data = await image.read()
    if len(image_data) > settings.max_upload_size_bytes:
        raise FileSizeExceededError(settings.max_upload_size_mb)

    conv_id = conversation_id or new_id()
    state = await agent.run(
        conversation_id=conv_id,
        user_message=message or "",
        locale=locale,
        image_data=image_data,
        image_content_type=image.content_type or "image/jpeg",
    )

    intent = state.get("intent")
    return ChatResponse(
        conversation_id=conv_id,
        message_id=state.get("assistant_message_id") or new_id(),
        answer=state.get("answer", ""),
        intent=intent.intent if intent else "image_search",
        products=state.get("products", []),
        widgets=state.get("widgets", []),
        sources=state.get("sources", []),
        debug=DebugInfo(
            used_rag=state.get("used_rag", False),
            used_product_search=state.get("used_product_search", False),
            used_image_analysis=state.get("used_image_analysis", False),
            intent_confidence=intent.confidence if intent else 1.0,
            detected_language=intent.detected_language if intent else "fa",
        ),
    )
