from __future__ import annotations

import logging

from backend.app.graph.state import AgentState
from backend.app.graph.nodes.react_controller import add_react_observation
from backend.app.tools.product_search import ProductSearchTool

logger = logging.getLogger(__name__)


def make_execute_product_search_node(product_tool: ProductSearchTool):
    async def execute_product_search(state: AgentState) -> AgentState:
        intent = state.get("intent")
        decision = state.get("react_decision")
        prior_products = state.get("last_products", [])
        query = (
            decision.action_input if decision and decision.action_input
            else (intent.search_query if intent else None) or state["user_message"]
        )

        reuse_prior_products = bool(prior_products) and intent and intent.intent in {
            "follow_up",
            "product_comparison",
            "product_detail",
        }
        if reuse_prior_products:
            products = prior_products
            price = intent.filters.price
            if price.min_toman is not None:
                products = [product for product in products if product.price >= price.min_toman]
            if price.max_toman is not None:
                products = [product for product in products if product.price <= price.max_toman]
        else:
            if intent and intent.intent == "follow_up" and state.get("last_image_analysis"):
                query = state["last_image_analysis"].suggested_search_query
            try:
                result = await product_tool.run(query=query, max_results=5)
                products = result.data.products if result.success and result.data else []
            except Exception as exc:
                logger.warning("Product search failed: %s", exc)
                products = []

        logger.debug("Product search returned %d products", len(products))
        return {
            **state,
            "products": products,
            "used_product_search": True,
            "react_steps": add_react_observation(state, f"Found {len(products)} product(s)."),
        }

    return execute_product_search
