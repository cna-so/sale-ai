from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.graph.nodes.react_controller import add_react_observation
from backend.app.tools.rag_search import RAGSearchTool

logger = logging.getLogger(__name__)


def make_execute_rag_node(rag_tool: RAGSearchTool):
    async def execute_rag(state: AgentState) -> AgentState:
        decision = state.get("react_decision")
        query = (
            decision.action_input if decision and decision.action_input
            else state.get("intent") and state["intent"].search_query or state["user_message"]
        )
        try:
            result = await rag_tool.run(query=query)
            docs = result.data if result.success else []
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            docs = []

        logger.debug("RAG retrieved %d documents", len(docs))
        return {
            **state,
            "retrieved_docs": docs,
            "used_rag": True,
            "react_steps": add_react_observation(state, f"Retrieved {len(docs)} document(s)."),
        }

    return execute_rag
