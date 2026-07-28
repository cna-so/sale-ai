from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.models.domain import ChatMessage, UserPreferences
from backend.app.repositories.conversation_repository import ConversationRepository
from backend.app.utils.ids import new_id
from backend.app.utils.language import parse_price_constraints

logger = logging.getLogger(__name__)


def make_save_conversation_node(repository: ConversationRepository):
    async def save_conversation(state: AgentState) -> AgentState:
        conversation_id = state["conversation_id"]
        user_message = state["user_message"]
        answer = state.get("answer", "")
        intent = state.get("intent")
        products = state.get("products", [])
        assistant_message_id = new_id()

        user_msg = ChatMessage(
            id=new_id(),
            role="user",
            content=user_message,
            intent=intent.intent if intent else None,
        )
        assistant_msg = ChatMessage(
            id=assistant_message_id,
            role="assistant",
            content=answer,
            intent=intent.intent if intent else None,
            recommended_product_ids=[p.id for p in products],
        )

        await repository.save_message(conversation_id, user_msg)
        await repository.save_message(conversation_id, assistant_msg)

        # Extract lightweight preferences
        if intent:
            min_t, max_t = intent.filters.price.min_toman, intent.filters.price.max_toman
            if min_t is not None or max_t is not None:
                current_prefs = state.get("preferences") or UserPreferences()
                updated = UserPreferences(
                    budget_min=min_t or current_prefs.budget_min,
                    budget_max=max_t or current_prefs.budget_max,
                    currency=state.get("currency", "IRR"),
                    preferred_categories=current_prefs.preferred_categories,
                    preferred_brands=current_prefs.preferred_brands,
                )
                await repository.update_preferences(conversation_id, updated)

        logger.debug("Saved conversation %s (assistant msg %s)", conversation_id, assistant_message_id)
        return {**state, "assistant_message_id": assistant_message_id}

    return save_conversation
