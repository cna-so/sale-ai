from __future__ import annotations

from typing import Any, TypedDict

from backend.app.models.domain import (
    ChatMessage,
    ImageAnalysisResult,
    IntentResult,
    Product,
    RetrievedDocument,
    UserPreferences,
)
from backend.app.schemas.react import ReActDecision, ReActStep


class AgentState(TypedDict, total=False):
    # Input
    conversation_id: str
    user_message: str
    locale: str
    currency: str

    # Image (optional, only for /chat/image route)
    image_data: bytes | None
    image_content_type: str | None

    # Context loaded from repository
    history: list[ChatMessage]
    preferences: UserPreferences

    # Intent
    intent: IntentResult

    # Tool outputs
    retrieved_docs: list[RetrievedDocument]
    products: list[Product]
    image_analysis: ImageAnalysisResult | None
    last_products: list[Product]
    last_image_analysis: ImageAnalysisResult | None

    # ReAct controller state (internal-only; never returned to API clients)
    react_decision: ReActDecision | None
    react_iteration: int
    react_steps: list[ReActStep]

    # Final output
    answer: str
    widgets: list[Any]
    sources: list[RetrievedDocument]

    # Debug flags
    used_rag: bool
    used_product_search: bool
    used_image_analysis: bool

    # Persistence
    assistant_message_id: str
    error: str | None
