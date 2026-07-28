from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from backend.app.models.domain import ChatMessage, Conversation, UserPreferences
from backend.app.repositories.conversation_repository import ConversationRepository

# Default maximum number of conversations retained in memory.
# Oldest-accessed entries are evicted once this limit is reached (LRU).
_DEFAULT_CAP = 1000


class InMemoryConversationRepository(ConversationRepository):
    """In-memory conversation store with LRU eviction.

    Conversations are kept in an :class:`~collections.OrderedDict` ordered by
    last access time.  When the number of conversations reaches *max_size*,
    the least-recently-used entry is evicted to prevent unbounded memory growth.
    """

    def __init__(self, max_size: int = _DEFAULT_CAP) -> None:
        self._store: OrderedDict[str, Conversation] = OrderedDict()
        self._max_size = max_size

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _touch(self, conversation_id: str) -> None:
        """Move *conversation_id* to the most-recently-used end."""
        self._store.move_to_end(conversation_id)

    def _evict_if_needed(self) -> None:
        """Remove the least-recently-used entry when the cap is exceeded."""
        while len(self._store) > self._max_size:
            evicted_id, _ = self._store.popitem(last=False)
            # last=False pops from the front (oldest / least-recently-used).

    # ------------------------------------------------------------------
    # ConversationRepository interface
    # ------------------------------------------------------------------

    async def get_or_create(self, conversation_id: str) -> Conversation:
        if conversation_id in self._store:
            self._touch(conversation_id)
            return self._store[conversation_id]
        conv = Conversation(id=conversation_id)
        self._store[conversation_id] = conv
        self._evict_if_needed()
        return conv

    async def get(self, conversation_id: str) -> Conversation | None:
        conv = self._store.get(conversation_id)
        if conv is not None:
            self._touch(conversation_id)
        return conv

    async def save_message(self, conversation_id: str, message: ChatMessage) -> None:
        conv = await self.get_or_create(conversation_id)
        conv.messages.append(message)
        conv.updated_at = datetime.now(timezone.utc)

    async def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        conv = await self.get(conversation_id)
        if conv is None:
            return []
        return list(conv.messages)

    async def update_preferences(self, conversation_id: str, preferences: UserPreferences) -> None:
        conv = await self.get_or_create(conversation_id)
        conv.preferences = preferences
        conv.updated_at = datetime.now(timezone.utc)
