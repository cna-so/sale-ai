from __future__ import annotations

import base64

import pytest

from backend.app.services.intent_service import IntentService


@pytest.fixture
def intent_service():
    return IntentService(None)


@pytest.mark.asyncio
async def test_gift_recommendation_intent_in_persian(intent_service):
    result = await intent_service.detect_intent("برای تولد مادرم یک هدیه زیر سه میلیون می‌خواهم")

    assert result.intent == "gift_recommendation"
    assert result.requires_product_search is True
    assert result.detected_language == "fa"


@pytest.mark.asyncio
async def test_product_comparison_intent_in_english(intent_service):
    result = await intent_service.detect_intent("What is the difference between these keyboards?")

    assert result.intent == "product_comparison"
    assert result.requires_product_search is True
    assert result.detected_language == "en"


@pytest.mark.asyncio
async def test_gift_search_returns_grounded_comparison_widget(test_agent):
    state = await test_agent.run(
        conversation_id="gift-shopping",
        user_message="I need a birthday gift under 3000000",
        locale="en-US",
    )

    assert state["intent"].intent == "gift_recommendation"
    assert state["products"]
    assert state["widgets"][0].type == "comparison_table"
    assert state["answer"]


@pytest.mark.asyncio
async def test_follow_up_reuses_persisted_products_for_product_detail(test_agent):
    conversation_id = "product-detail"
    first = await test_agent.run(conversation_id, "I want to buy a mechanical keyboard", locale="en-US")
    second = await test_agent.run(conversation_id, "Tell me about the first option", locale="en-US")

    assert first["products"]
    assert second["intent"].intent == "product_detail"
    assert second["products"][0].id == first["products"][0].id
    assert second["widgets"][0].type == "product_card"


@pytest.mark.asyncio
async def test_image_search_context_is_available_to_follow_up(test_agent):
    conversation_id = "image-continuity"
    first = await test_agent.run(
        conversation_id,
        "Find similar products",
        locale="en-US",
        image_data=b"image-data",
        image_content_type="image/jpeg",
    )
    second = await test_agent.run(conversation_id, "Show me cheaper ones", locale="en-US")

    assert first["image_analysis"] is not None
    assert second["last_image_analysis"] is not None
    assert second["used_product_search"] is True


def test_openai_compatible_image_completion(client):
    image_url = "data:image/jpeg;base64," + base64.b64encode(b"image-data").decode()
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "conversation_id": "oai-image",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Find similar products"},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "این یک پاسخ آزمایشی است." in content
