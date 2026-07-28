from __future__ import annotations

import pytest

from backend.app.services.intent_service import IntentService


@pytest.fixture
def intent_service():
    return IntentService(llm_service=None)


@pytest.mark.asyncio
async def test_product_search_intent_fa(intent_service):
    result = await intent_service.detect_intent("یک کیبورد گیمینگ می‌خوام")
    assert result.intent == "product_search"
    assert result.detected_language == "fa"


@pytest.mark.asyncio
async def test_recommendation_intent_fa_with_budget(intent_service):
    result = await intent_service.detect_intent("بهترین هدفون زیر ۳ میلیون")
    assert result.intent == "recommendation"
    assert result.filters.price.max_toman == 3_000_000


@pytest.mark.asyncio
async def test_product_search_intent_en(intent_service):
    result = await intent_service.detect_intent("I want to buy a mechanical keyboard")
    assert result.intent == "product_search"
    assert result.detected_language == "en"


@pytest.mark.asyncio
async def test_rag_intent_fa(intent_service):
    result = await intent_service.detect_intent("سیاست بازگشت کالا چیست")
    assert result.intent == "rag_query"
    assert result.requires_rag is True


@pytest.mark.asyncio
async def test_rag_intent_en(intent_service):
    result = await intent_service.detect_intent("What is the return policy?")
    assert result.intent == "rag_query"


@pytest.mark.asyncio
async def test_recommendation_intent_en(intent_service):
    result = await intent_service.detect_intent("recommend a headphone under 5000000")
    assert result.intent in ("recommendation", "product_search")


@pytest.mark.asyncio
async def test_general_chat_fallback(intent_service):
    result = await intent_service.detect_intent("سلام")
    assert result.intent == "general_chat"
    assert result.detected_language == "fa"
