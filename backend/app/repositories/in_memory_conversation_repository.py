from __future__ import annotations

from datetime import datetime

from backend.app.models.domain import ChatMessage, Conversation, UserPreferences
from backend.app.repositories.conversation_repository import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._store: dict[str, Conversation] = {}

    async def get_or_create(self, conversation_id: str) -> Conversation:
        existing = self._store.get(conversation_id)
        if existing is not None:
            return existing
        conv = Conversation(id=conversation_id)
        self._store[conversation_id] = conv
        return conv

    async def get(self, conversation_id: str) -> Conversation | None:
        return self._store.get(conversation_id)

    async def save_message(self, conversation_id: str, message: ChatMessage) -> None:
        conv = await self.get_or_create(conversation_id)
        conv.messages.append(message)
        conv.updated_at = datetime.utcnow()

    async def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        conv = await self.get(conversation_id)
        if conv is None:
            return []
        return list(conv.messages)

    async def update_preferences(self, conversation_id: str, preferences: UserPreferences) -> None:
        conv = await self.get_or_create(conversation_id)
        conv.preferences = preferences
        conv.updated_at = datetime.utcnow()
