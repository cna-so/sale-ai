from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import app
from backend.app.api.dependencies import (
    get_conversation_repository,
    get_llm_service,
    get_product_provider,
    get_shopping_agent,
    get_intent_service,
)
from backend.app.providers.mock_product_provider import MockProductProvider
from backend.app.repositories.in_memory_conversation_repository import InMemoryConversationRepository
from backend.app.services.intent_service import IntentService
from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.graph.builder import build_shopping_graph
from backend.app.services.llm_service import LLMService
from backend.app.services.product_service import ProductService
from backend.app.services.recommendation_service import RecommendationService
from backend.app.tools.image_understanding import ImageUnderstandingTool
from backend.app.tools.product_search import ProductSearchTool
from backend.app.tools.rag_search import RAGSearchTool
from backend.app.rag.retrieval_service import RetrievalService


@pytest.fixture
def test_settings():
    return Settings(
        app_env="test",
        openrouter_api_key="",
        product_provider="mock",
        qdrant_host="localhost",
        qdrant_port=6333,
    )


@pytest.fixture
def mock_repo():
    return InMemoryConversationRepository()


@pytest.fixture
def mock_provider():
    return MockProductProvider()


class FakeLLMService:
    """LLM stub that never makes real HTTP calls."""
    async def chat(self, messages, **kwargs):
        last = messages[-1]["content"] if messages else ""
        if "json" in str(kwargs.get("response_format", "")):
            return '{"intent": "product_search", "confidence": 0.9, "search_query": "keyboard", "filters": {"price": {}, "category": null, "brand": null, "color": null}, "requires_rag": false, "requires_product_search": true, "detected_language": "fa"}'
        return "این یک پاسخ آزمایشی است."

    async def chat_with_image(self, **kwargs):
        return '{"product_category": "electronics", "concise_description": "gaming keyboard", "visual_attributes": ["rgb", "mechanical"], "suggested_search_query": "کیبورد گیمینگ", "confidence": 0.85}'


class FakeRetrievalService:
    async def retrieve(self, query, top_k=5, collection=None):
        return []


@pytest.fixture
def fake_llm():
    return FakeLLMService()


@pytest.fixture
def fake_retrieval():
    return FakeRetrievalService()


@pytest.fixture
def test_agent(test_settings, mock_repo, mock_provider, fake_llm, fake_retrieval):
    product_service = ProductService(mock_provider)
    product_tool = ProductSearchTool(product_service)
    rag_tool = RAGSearchTool(fake_retrieval)
    image_tool = ImageUnderstandingTool(fake_llm)
    intent_service = IntentService(None)  # fallback only
    rec_service = RecommendationService()

    graph = build_shopping_graph(
        repository=mock_repo,
        settings=test_settings,
        intent_service=intent_service,
        rag_tool=rag_tool,
        product_tool=product_tool,
        image_tool=image_tool,
        llm_service=fake_llm,
        recommendation_service=rec_service,
    )
    return ShoppingAgent(graph)


@pytest.fixture
def client(test_settings, test_agent, mock_repo):
    def override_settings():
        return test_settings

    def override_agent():
        return test_agent

    def override_repo():
        return mock_repo

    def override_intent():
        return IntentService(None)

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_shopping_agent] = override_agent
    app.dependency_overrides[get_conversation_repository] = override_repo
    app.dependency_overrides[get_intent_service] = override_intent

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
