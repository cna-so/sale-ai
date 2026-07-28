from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.app.graph.nodes.detect_intent import make_detect_intent_node
from backend.app.graph.nodes.execute_image_search import make_execute_image_search_node
from backend.app.graph.nodes.execute_product_search import make_execute_product_search_node
from backend.app.graph.nodes.execute_rag import make_execute_rag_node
from backend.app.graph.nodes.generate_response import make_generate_response_node
from backend.app.graph.nodes.load_context import make_load_context_node
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
            -> execute_rag         (rag_query)
            -> execute_product_search (product_search | recommendation | follow_up)
            -> execute_image_search   (image_search)
            -> generate_response      (general_chat directly)
        -> generate_response
        -> save_conversation
        -> END
    """
    graph = StateGraph(AgentState)

    # --- Register nodes ---
    graph.add_node("load_context", make_load_context_node(repository, settings))
    graph.add_node("detect_intent", make_detect_intent_node(intent_service))
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
            "rag_query": "execute_rag",
            "product_search": "execute_product_search",
            "recommendation": "execute_product_search",
            "follow_up": "execute_product_search",
            "image_search": "execute_image_search",
        },
    )

    # --- All tool nodes converge on generate_response ---
    graph.add_edge("execute_rag", "generate_response")
    graph.add_edge("execute_product_search", "generate_response")
    graph.add_edge("execute_image_search", "generate_response")

    # --- Save then end ---
    graph.add_edge("generate_response", "save_conversation")
    graph.add_edge("save_conversation", END)

    return graph.compile()
