from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.domain import Product, RetrievedDocument
from backend.app.schemas.widgets import Widget


class ChatMetadata(BaseModel):
    currency: str = Field(default="IRR")
    locale: str = Field(default="fa-IR")


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None)
    message: str = Field(min_length=1, max_length=4000)
    metadata: ChatMetadata = Field(default_factory=ChatMetadata)


class DebugInfo(BaseModel):
    used_rag: bool = False
    used_product_search: bool = False
    used_image_analysis: bool = False
    intent_confidence: float = 1.0
    detected_language: str = "fa"


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    intent: str
    products: list[Product] = Field(default_factory=list)
    widgets: list[Widget] = Field(default_factory=list)
    sources: list[RetrievedDocument] = Field(default_factory=list)
    debug: DebugInfo = Field(default_factory=DebugInfo)


class ImageChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None)
    message: str | None = Field(default=None)
    locale: str = Field(default="fa-IR")
