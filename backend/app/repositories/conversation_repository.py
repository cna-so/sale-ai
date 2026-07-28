from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.models.domain import ChatMessage, Conversation, UserPreferences


class ConversationRepository(ABC):
    @abstractmethod
    async def get_or_create(self, conversation_id: str) -> Conversation:
        ...

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None:
        ...

    @abstractmethod
    async def save_message(self, conversation_id: str, message: ChatMessage) -> None:
        ...

    @abstractmethod
    async def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        ...

    @abstractmethod
    async def update_preferences(self, conversation_id: str, preferences: UserPreferences) -> None:
        ...
