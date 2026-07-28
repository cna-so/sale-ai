from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RAGSearchInput(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    collection: str | None = None


class ProductSearchInput(BaseModel):
    query: str
    max_results: int = Field(default=5, ge=1, le=20)
    locale: str = Field(default="fa-IR")


class ImageUnderstandingInput(BaseModel):
    image_data: bytes
    content_type: str
    instruction: str | None = None
    locale: str = Field(default="fa-IR")


class MemoryRetrievalInput(BaseModel):
    conversation_id: str
    last_n: int = Field(default=12, ge=1, le=50)
