from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.models.domain import Product


class ProductSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=20)
    locale: str = Field(default="fa-IR")


class ProductSearchResponse(BaseModel):
    products: list[Product]
    query: str
    provider: str
    total: int
