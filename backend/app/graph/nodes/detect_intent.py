from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.services.intent_service import IntentService
from backend.app.utils.language import detect_language

logger = logging.getLogger(__name__)


def make_detect_intent_node(intent_service: IntentService):
    async def detect_intent(state: AgentState) -> AgentState:
        history = state.get("history", [])
        history_texts = [m.content for m in history]

        # Image path: always classify as image_search
        if state.get("image_data") is not None:
            from backend.app.models.domain import IntentResult
            message = state.get("user_message", "")
            language = detect_language(message) if message else (
                "fa" if state.get("locale", "").startswith("fa") else "en"
            )
            intent = IntentResult(
                intent="image_search",
                confidence=1.0,
                search_query=message,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )
            return {**state, "intent": intent}

        intent = await intent_service.detect_intent(
            message=state["user_message"],
            conversation_messages=history_texts,
        )
        logger.info("Intent detected: %s (%.2f) lang=%s", intent.intent, intent.confidence, intent.detected_language)
        return {**state, "intent": intent}

    return detect_intent
