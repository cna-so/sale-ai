from __future__ import annotations

import logging

from backend.app.core.exceptions import ImageProcessingError
from backend.app.graph.state import AgentState
from backend.app.graph.nodes.react_controller import add_react_observation
from backend.app.tools.image_understanding import ImageUnderstandingTool
from backend.app.tools.product_search import ProductSearchTool

logger = logging.getLogger(__name__)


def make_execute_image_search_node(image_tool: ImageUnderstandingTool, product_tool: ProductSearchTool):
    async def execute_image_search(state: AgentState) -> AgentState:
        image_data = state.get("image_data")
        content_type = state.get("image_content_type", "image/jpeg")
        decision = state.get("react_decision")
        instruction = (
            decision.action_input if decision and decision.action_input
            else state.get("user_message") or None
        )
        locale = state.get("locale", "fa-IR")

        image_analysis = None
        products = []

        if image_data:
            try:
                tool_result = await image_tool.run(
                    image_data=image_data,
                    content_type=content_type,
                    instruction=instruction,
                    locale=locale,
                )
                image_analysis = tool_result.data

                search_query = image_analysis.suggested_search_query
                product_result = await product_tool.run(query=search_query, max_results=5)
                products = product_result.data.products if product_result.success and product_result.data else []
            except ImageProcessingError as exc:
                logger.warning("Image processing error: %s", exc)
            except Exception as exc:
                logger.warning("Image search pipeline failed: %s", exc)

        return {
            **state,
            "image_analysis": image_analysis,
            "products": products,
            "used_image_analysis": True,
            "used_product_search": len(products) > 0,
            "react_steps": add_react_observation(
                state,
                f"Analyzed image and found {len(products)} product(s).",
            ),
        }

    return execute_image_search
