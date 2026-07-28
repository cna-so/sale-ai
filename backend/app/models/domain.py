from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(BaseModel):
    id: str = Field(default="", description="Internal product ID")
    title: str = Field(description="Persian product title")
    title_en: str = Field(default="", description="English title or transliteration")
    image_url: str = Field(default="", description="Product image URL")
    price: int = Field(default=0, description="Price in Toman")
    currency: str = Field(default="IRR")
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    product_url: str = Field(default="", description="Full product URL")
    source: str = Field(default="unknown", description="Data source identifier")
    available: bool = Field(default=True)


class ProductSearchResult(BaseModel):
    products: list[Product] = Field(default_factory=list)
    query: str = Field(default="")
    provider: str = Field(default="unknown")
    total_found: int = Field(default=0)
    error: str | None = Field(default=None)


class Recommendation(BaseModel):
    product: Product
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance score")
    reason: str = Field(default="", description="Why this is recommended")


# ---------------------------------------------------------------------------
# Documents / RAG
# ---------------------------------------------------------------------------

class RetrievedDocument(BaseModel):
    content: str
    source: str = Field(default="")
    title: str = Field(default="")
    chunk_index: int = Field(default=0)
    document_id: str = Field(default="")
    score: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# Conversation / Memory
# ---------------------------------------------------------------------------

class UserPreferences(BaseModel):
    budget_max: int | None = Field(default=None, description="Max budget in Toman")
    budget_min: int | None = Field(default=None, description="Min budget in Toman")
    currency: str = Field(default="IRR")
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_sizes: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    id: str = Field(description="Message UUID")
    role: str = Field(description="'user' or 'assistant'")
    content: str
    intent: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recommended_product_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(description="Conversation UUID")
    messages: list[ChatMessage] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

class PriceFilter(BaseModel):
    min_toman: int | None = None
    max_toman: int | None = None


class IntentFilters(BaseModel):
    price: PriceFilter = Field(default_factory=PriceFilter)
    category: str | None = None
    brand: str | None = None
    color: str | None = None


class IntentResult(BaseModel):
    intent: str = Field(description="Detected intent label")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    search_query: str = Field(default="", description="Normalized search query")
    filters: IntentFilters = Field(default_factory=IntentFilters)
    requires_rag: bool = False
    requires_product_search: bool = False
    detected_language: str = Field(default="fa", description="'fa' or 'en'")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None


class ImageAnalysisResult(BaseModel):
    product_category: str
    concise_description: str
    visual_attributes: list[str] = Field(default_factory=list)
    suggested_search_query: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
