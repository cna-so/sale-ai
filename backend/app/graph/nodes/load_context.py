from __future__ import annotations

import logging

from backend.app.core.config import Settings
from backend.app.graph.state import AgentState
from backend.app.models.domain import ImageAnalysisResult, Product, UserPreferences
from backend.app.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


def make_load_context_node(repository: ConversationRepository, settings: Settings):
    async def load_context(state: AgentState) -> AgentState:
        conversation_id = state["conversation_id"]
        conv = await repository.get_or_create(conversation_id)
        limit = settings.chat_history_limit
        repo_history = conv.messages[-limit:] if conv.messages else []
        # LibreChat / OpenAI clients already send the thread; prefer that for continuity.
        client_history = state.get("client_history") or []
        history = (client_history or repo_history)[-limit:]

        last_products: list[Product] = []
        last_image_analysis = None
        # Prefer metadata from our persisted assistant turns; fall back to client history.
        for message in reversed([*repo_history, *client_history]):
            if message.role != "assistant":
                continue
            metadata = message.metadata or {}
            if not last_products:
                try:
                    last_products = [
                        Product.model_validate(product)
                        for product in metadata.get("products", [])
                    ]
                except (TypeError, ValueError):
                    logger.warning("Skipping invalid persisted product context")
            if last_image_analysis is None and metadata.get("image_analysis"):
                try:
                    last_image_analysis = ImageAnalysisResult.model_validate(metadata["image_analysis"])
                except (TypeError, ValueError):
                    logger.warning("Skipping invalid persisted image context")
            if last_products and last_image_analysis is not None:
                break
        logger.info(
            "Loaded %d history messages for conversation %s (client=%d repo=%d)",
            len(history),
            conversation_id,
            len(client_history),
            len(repo_history),
        )
        return {
            **state,
            "history": history,
            "preferences": conv.preferences,
            "last_products": last_products,
            "last_image_analysis": last_image_analysis,
        }

    return load_context
