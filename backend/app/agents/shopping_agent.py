from __future__ import annotations

import logging
from typing import Any

from backend.app.graph.builder import build_shopping_graph
from backend.app.graph.state import AgentState
from backend.app.models.domain import UserPreferences

logger = logging.getLogger(__name__)


class ShoppingAgent:
    """
    Entry point for running the LangGraph shopping workflow.
    Wraps the compiled graph and exposes a clean async interface.
    """

    def __init__(self, graph) -> None:
        self._graph = graph

    async def run(
        self,
        conversation_id: str,
        user_message: str,
        locale: str = "fa-IR",
        currency: str = "IRR",
        image_data: bytes | None = None,
        image_content_type: str | None = None,
    ) -> AgentState:
        initial_state: AgentState = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "locale": locale,
            "currency": currency,
            "image_data": image_data,
            "image_content_type": image_content_type,
            "history": [],
            "preferences": UserPreferences(),
            "retrieved_docs": [],
            "products": [],
            "image_analysis": None,
            "last_products": [],
            "last_image_analysis": None,
            "react_decision": None,
            "react_iteration": 0,
            "react_steps": [],
            "answer": "",
            "widgets": [],
            "sources": [],
            "used_rag": False,
            "used_product_search": False,
            "used_image_analysis": False,
            "assistant_message_id": "",
            "error": None,
        }

        try:
            final_state: AgentState = await self._graph.ainvoke(initial_state)
        except Exception as exc:
            logger.error("Agent graph execution failed: %s", exc, exc_info=True)
            initial_state["answer"] = "\u062e\u0637\u0627\u06cc \u062f\u0627\u062e\u0644\u06cc \u0631\u062e \u062f\u0627\u062f. \u0644\u0637\u0641\u0627\u064b \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f."
            initial_state["error"] = str(exc)
            return initial_state

        return final_state
