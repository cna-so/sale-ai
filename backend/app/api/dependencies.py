from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from backend.app.agents.shopping_agent import ShoppingAgent
from backend.app.core.config import Settings, get_settings
from backend.app.graph.builder import build_shopping_graph
from backend.app.providers.digikala_playwright_provider import DigikalaPlaywrightProvider
from backend.app.providers.mock_product_provider import MockProductProvider
from backend.app.providers.product_provider import ProductProvider
from backend.app.rag.indexing_service import IndexingService
from backend.app.rag.retrieval_service import RetrievalService
from backend.app.repositories.conversation_repository import ConversationRepository
from backend.app.repositories.in_memory_conversation_repository import InMemoryConversationRepository
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.intent_service import IntentService
from backend.app.services.llm_service import LLMService
from backend.app.services.product_service import ProductService
from backend.app.services.recommendation_service import RecommendationService
from backend.app.tools.image_understanding import ImageUnderstandingTool
from backend.app.tools.product_search import ProductSearchTool
from backend.app.tools.rag_search import RAGSearchTool
from backend.app.vectorstore.qdrant_client import get_qdrant_client

# ---------------------------------------------------------------------------
# Module-level singletons (process-wide)
# ---------------------------------------------------------------------------

_repo: InMemoryConversationRepository | None = None
_llm: LLMService | None = None
_embedding: EmbeddingService | None = None
_agent: ShoppingAgent | None = None


def get_conversation_repository(settings: Settings = Depends(get_settings)) -> ConversationRepository:
    global _repo
    if _repo is None:
        _repo = InMemoryConversationRepository()
    return _repo


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    global _llm
    if _llm is None:
        _llm = LLMService(settings)
    return _llm


def get_embedding_service(settings: Settings = Depends(get_settings)) -> EmbeddingService:
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingService(settings)
    return _embedding


def get_product_provider(settings: Settings = Depends(get_settings)) -> ProductProvider:
    if settings.product_provider == "digikala":
        return DigikalaPlaywrightProvider(settings)
    return MockProductProvider()


def get_product_service(provider: ProductProvider = Depends(get_product_provider)) -> ProductService:
    return ProductService(provider)


def get_product_tool(service: ProductService = Depends(get_product_service)) -> ProductSearchTool:
    return ProductSearchTool(service)


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


def get_intent_service(
    settings: Settings = Depends(get_settings),
    llm: LLMService = Depends(get_llm_service),
) -> IntentService:
    if settings.is_openrouter_configured:
        return IntentService(llm)
    return IntentService(None)


def get_qdrant(settings: Settings = Depends(get_settings)):
    return get_qdrant_client(settings)


def get_retrieval_service(
    settings: Settings = Depends(get_settings),
    embedding: EmbeddingService = Depends(get_embedding_service),
    qdrant=Depends(get_qdrant),
) -> RetrievalService:
    return RetrievalService(settings, embedding, qdrant)


def get_indexing_service(
    settings: Settings = Depends(get_settings),
    embedding: EmbeddingService = Depends(get_embedding_service),
    qdrant=Depends(get_qdrant),
) -> IndexingService:
    return IndexingService(settings, embedding, qdrant)


def get_rag_tool(retrieval: RetrievalService = Depends(get_retrieval_service)) -> RAGSearchTool:
    return RAGSearchTool(retrieval)


def get_image_tool(llm: LLMService = Depends(get_llm_service)) -> ImageUnderstandingTool:
    return ImageUnderstandingTool(llm)


def get_shopping_agent(
    settings: Settings = Depends(get_settings),
    repo: ConversationRepository = Depends(get_conversation_repository),
    intent: IntentService = Depends(get_intent_service),
    rag_tool: RAGSearchTool = Depends(get_rag_tool),
    product_tool: ProductSearchTool = Depends(get_product_tool),
    image_tool: ImageUnderstandingTool = Depends(get_image_tool),
    llm: LLMService = Depends(get_llm_service),
    rec: RecommendationService = Depends(get_recommendation_service),
) -> ShoppingAgent:
    graph = build_shopping_graph(
        repository=repo,
        settings=settings,
        intent_service=intent,
        rag_tool=rag_tool,
        product_tool=product_tool,
        image_tool=image_tool,
        llm_service=llm,
        recommendation_service=rec,
    )
    return ShoppingAgent(graph)
