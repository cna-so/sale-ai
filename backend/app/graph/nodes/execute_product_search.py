from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.tools.product_search import ProductSearchTool

logger = logging.getLogger(__name__)


def make_execute_product_search_node(product_tool: ProductSearchTool):
    async def execute_product_search(state: AgentState) -> AgentState:
        intent = state.get("intent")
        query = (intent.search_query if intent else None) or state["user_message"]

        try:
            result = await product_tool.run(query=query, max_results=5)
            products = result.data.products if result.success and result.data else []
        except Exception as exc:
            logger.warning("Product search failed: %s", exc)
            products = []

        logger.debug("Product search returned %d products", len(products))
        return {**state, "products": products, "used_product_search": True}

    return execute_product_search
