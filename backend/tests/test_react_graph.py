from __future__ import annotations

import json

import pytest

from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.core.config import Settings
from backend.app.graph.builder import build_shopping_graph
from backend.app.graph.nodes.execute_product_search import make_execute_product_search_node
from backend.app.graph.nodes.react_controller import (
    route_after_react_controller,
)
from backend.app.models.domain import Product, ProductSearchResult, ToolResult
from backend.app.providers.mock_product_provider import MockProductProvider
from backend.app.repositories.in_memory_conversation_repository import InMemoryConversationRepository
from backend.app.services.intent_service import IntentService
from backend.app.services.product_service import ProductService
from backend.app.services.recommendation_service import RecommendationService
from backend.app.tools.image_understanding import ImageUnderstandingTool
from backend.app.tools.product_search import ProductSearchTool
from backend.app.tools.rag_search import RAGSearchTool
from backend.app.schemas.react import ReActDecision


class ScriptedLLM:
    def __init__(self, decisions: list[dict] | None = None) -> None:
        self._decisions = iter(decisions or [])
        self.controller_calls = 0

    async def chat(self, messages, **kwargs):
        if kwargs.get("response_format"):
            self.controller_calls += 1
            try:
                return json.dumps(next(self._decisions))
            except StopIteration:
                return "not valid JSON"
        return "Final synthesized answer."

    async def chat_with_image(self, **kwargs):
        return json.dumps(
            {
                "product_category": "electronics",
                "concise_description": "keyboard",
                "visual_attributes": ["mechanical"],
                "suggested_search_query": "gaming keyboard",
                "confidence": 0.9,
            }
        )


class RetrievalWithDocument:
    async def retrieve(self, query, top_k=5, collection=None):
        from backend.app.models.domain import RetrievedDocument

        return [RetrievedDocument(content="Returns are accepted for seven days.", source="policy.md")]


class ProductToolSpy:
    def __init__(self) -> None:
        self.query = ""

    async def run(self, query, max_results=5):
        self.query = query
        return ToolResult(
            tool_name="product_search",
            success=True,
            data=ProductSearchResult(
                query=query,
                products=[Product(id="p1", title="Keyboard", price=1_000_000)],
            ),
        )


def build_agent(*, llm: ScriptedLLM, settings: Settings, retrieval=None) -> ShoppingAgent:
    repository = InMemoryConversationRepository()
    provider = MockProductProvider()
    product_tool = ProductSearchTool(ProductService(provider))
    rag_tool = RAGSearchTool(retrieval or RetrievalWithDocument())
    return ShoppingAgent(
        build_shopping_graph(
            repository=repository,
            settings=settings,
            intent_service=IntentService(None),
            rag_tool=rag_tool,
            product_tool=product_tool,
            image_tool=ImageUnderstandingTool(llm),
            llm_service=llm,
            recommendation_service=RecommendationService(),
        )
    )


def test_react_route_selection():
    assert route_after_react_controller(
        {
            "react_decision": ReActDecision(
                next_action="product_search",
                should_continue=True,
            )
        }
    ) == "product_search"
    assert route_after_react_controller(
        {"react_decision": ReActDecision(next_action="stop", should_continue=False)}
    ) == "generate_response"


@pytest.mark.asyncio
async def test_product_action_uses_react_action_input_and_updates_state():
    tool = ProductToolSpy()
    node = make_execute_product_search_node(tool)
    state = await node(
        {
            "user_message": "ignored",
            "react_decision": ReActDecision(
                next_action="product_search",
                action_input="wireless keyboard",
                reason="Search products.",
                should_continue=True,
            ),
            "react_steps": [],
        }
    )

    assert tool.query == "wireless keyboard"
    assert state["used_product_search"] is True
    assert state["products"][0].id == "p1"


@pytest.mark.asyncio
async def test_react_loop_terminates_at_configured_limit():
    llm = ScriptedLLM(
        [
            {
                "next_action": "product_search",
                "action_input": "keyboard",
                "reason": "Search products.",
                "should_continue": True,
            }
        ]
    )
    settings = Settings(app_env="test", react_max_iterations=1)
    agent = build_agent(llm=llm, settings=settings)

    state = await agent.run("bounded", "I want to buy a keyboard", locale="en-US")

    assert state["react_iteration"] == 2
    assert state["react_steps"][-1].action == "stop"
    assert state["products"]
    assert state["answer"] == "Final synthesized answer."


@pytest.mark.asyncio
async def test_persian_product_query_runs_loop_and_generates_widgets():
    llm = ScriptedLLM()
    agent = build_agent(llm=llm, settings=Settings(app_env="test"))

    state = await agent.run("persian-product", "یک کیبورد گیمینگ می‌خوام")

    assert state["intent"].detected_language == "fa"
    assert state["used_product_search"] is True
    assert state["react_steps"][0].action == "product_search"
    assert state["answer"] == "Final synthesized answer."
    assert state["widgets"]


@pytest.mark.asyncio
async def test_persian_rag_query_uses_rag_then_final_answer():
    llm = ScriptedLLM()
    agent = build_agent(llm=llm, settings=Settings(app_env="test"))

    state = await agent.run("persian-rag", "سیاست بازگشت کالا چیست")

    assert state["used_rag"] is True
    assert state["retrieved_docs"][0].source == "policy.md"
    assert state["answer"] == "Final synthesized answer."


@pytest.mark.asyncio
async def test_image_query_uses_image_action_and_product_results():
    llm = ScriptedLLM()
    agent = build_agent(llm=llm, settings=Settings(app_env="test"))

    state = await agent.run(
        "image-query",
        "Find this product",
        locale="en-US",
        image_data=b"image-data",
        image_content_type="image/jpeg",
    )

    assert state["intent"].intent == "image_search"
    assert state["used_image_analysis"] is True
    assert state["products"]
    assert state["answer"] == "Final synthesized answer."
