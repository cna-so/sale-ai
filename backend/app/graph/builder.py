from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.app.graph.nodes.detect_intent import make_detect_intent_node
from backend.app.graph.nodes.execute_image_search import make_execute_image_search_node
from backend.app.graph.nodes.execute_product_search import make_execute_product_search_node
from backend.app.graph.nodes.execute_rag import make_execute_rag_node
from backend.app.graph.nodes.generate_response import make_generate_response_node
from backend.app.graph.nodes.load_context import make_load_context_node
from backend.app.graph.nodes.react_controller import (
    make_react_controller_node,
    route_after_react_controller,
)
from backend.app.graph.nodes.route_request import route_by_intent
from backend.app.graph.nodes.save_conversation import make_save_conversation_node
from backend.app.graph.state import AgentState


def build_shopping_graph(
    repository,
    settings,
    intent_service,
    rag_tool,
    product_tool,
    image_tool,
    llm_service,
    recommendation_service,
):
    """
    Build and compile the LangGraph shopping agent.

    Flow:
      load_context
        -> detect_intent
        -> route_request (conditional)
            -> react_controller (tool-eligible intents)
            -> generate_response (general_chat directly)
        -> react_controller -> action (conditional) -> react_controller
        -> generate_response (when enough context is available)
        -> save_conversation
        -> END
    """
    graph = StateGraph(AgentState)

    # --- Register nodes ---
    graph.add_node("load_context", make_load_context_node(repository, settings))
    graph.add_node("detect_intent", make_detect_intent_node(intent_service))
    graph.add_node("react_controller", make_react_controller_node(llm_service, settings))
    graph.add_node("execute_rag", make_execute_rag_node(rag_tool))
    graph.add_node("execute_product_search", make_execute_product_search_node(product_tool))
    graph.add_node("execute_image_search", make_execute_image_search_node(image_tool, product_tool))
    graph.add_node(
        "generate_response",
        make_generate_response_node(llm_service, recommendation_service),
    )
    graph.add_node("save_conversation", make_save_conversation_node(repository))

    # --- Entry point ---
    graph.set_entry_point("load_context")

    # --- Linear edges ---
    graph.add_edge("load_context", "detect_intent")

    # --- Conditional routing after intent detection ---
    graph.add_conditional_edges(
        "detect_intent",
        route_by_intent,
        {
            "general_chat": "generate_response",
            "rag_query": "react_controller",
            "product_search": "react_controller",
            "recommendation": "react_controller",
            "gift_recommendation": "react_controller",
            "product_comparison": "react_controller",
            "product_detail": "react_controller",
            "follow_up": "react_controller",
            "image_search": "react_controller",
        },
    )

    # --- Bounded ReAct controller/action loop ---
    graph.add_conditional_edges(
        "react_controller",
        route_after_react_controller,
        {
            "rag_search": "execute_rag",
            "product_search": "execute_product_search",
            "image_search": "execute_image_search",
            "generate_response": "generate_response",
        },
    )
    graph.add_edge("execute_rag", "react_controller")
    graph.add_edge("execute_product_search", "react_controller")
    graph.add_edge("execute_image_search", "react_controller")

    # --- Save then end ---
    graph.add_edge("generate_response", "save_conversation")
    graph.add_edge("save_conversation", END)

    return graph.compile()
