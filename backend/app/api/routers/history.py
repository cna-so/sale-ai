from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_conversation_repository
from backend.app.core.exceptions import ConversationNotFoundError
from backend.app.repositories.conversation_repository import ConversationRepository
from backend.app.schemas.history import HistoryResponse

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    conversation_id: str = Query(..., description="Conversation ID"),
    repo: ConversationRepository = Depends(get_conversation_repository),
):
    conv = await repo.get(conversation_id)
    if conv is None:
        raise ConversationNotFoundError(conversation_id)

    return HistoryResponse(
        conversation_id=conversation_id,
        messages=conv.messages,
        total=len(conv.messages),
    )
