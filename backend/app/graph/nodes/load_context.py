from __future__ import annotations

import logging

from backend.app.core.config import Settings
from backend.app.graph.state import AgentState
from backend.app.models.domain import UserPreferences
from backend.app.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


def make_load_context_node(repository: ConversationRepository, settings: Settings):
    async def load_context(state: AgentState) -> AgentState:
        conversation_id = state["conversation_id"]
        conv = await repository.get_or_create(conversation_id)
        limit = settings.chat_history_limit
        history = conv.messages[-limit:] if conv.messages else []
        logger.debug("Loaded %d messages for conversation %s", len(history), conversation_id)
        return {
            **state,
            "history": history,
            "preferences": conv.preferences,
        }

    return load_context
