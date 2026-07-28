from __future__ import annotations

from pydantic import BaseModel

from backend.app.models.domain import ChatMessage


class HistoryResponse(BaseModel):
    conversation_id: str
    messages: list[ChatMessage]
    total: int
