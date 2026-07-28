from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.tools.rag_search import RAGSearchTool

logger = logging.getLogger(__name__)


def make_execute_rag_node(rag_tool: RAGSearchTool):
    async def execute_rag(state: AgentState) -> AgentState:
        query = state.get("intent") and state["intent"].search_query or state["user_message"]
        try:
            result = await rag_tool.run(query=query)
            docs = result.data if result.success else []
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            docs = []

        logger.debug("RAG retrieved %d documents", len(docs))
        return {**state, "retrieved_docs": docs, "used_rag": True}

    return execute_rag
