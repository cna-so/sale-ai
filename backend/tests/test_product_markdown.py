from __future__ import annotations

from backend.app.models.domain import Product
from backend.app.schemas.widgets import (
    ProductCardData,
    ProductCardWidget,
)
from backend.app.utils.product_markdown import (
    build_shopping_chat_content,
    format_product_card,
    format_product_cards,
)


def _sample_product(**overrides) -> Product:
    data = {
        "id": "p1",
        "title": "کیبورد گیمینگ مکانیکی",
        "title_en": "Mechanical Gaming Keyboard",
        "image_url": "https://example.com/keyboard.jpg",
        "price": 2_850_000,
        "rating": 4.5,
        "product_url": "https://www.digikala.com/product/dkp-1/",
        "source": "mock",
    }
    data.update(overrides)
    return Product(**data)


def test_format_product_card_persian_includes_image_and_link():
    md = format_product_card(_sample_product(description="کیبورد مناسب هدیه", highlights=["گیمینگ"]), language="fa", reason="مناسب هدیه")
    assert "### کیبورد گیمینگ مکانیکی" in md
    assert "![کیبورد گیمینگ مکانیکی](https://example.com/keyboard.jpg)" in md
    assert "قیمت" in md
    assert "امتیاز" in md
    assert "جزئیات" in md
    assert "چرا مناسب است" in md
    assert "[مشاهده و خرید در دیجی‌کالا](https://www.digikala.com/product/dkp-1/)" in md


def test_format_product_cards_english_without_images():
    products = [
        _sample_product(),
        _sample_product(id="p2", title_en="Budget Keyboard", price=1_950_000),
    ]
    md = format_product_cards(
        products,
        language="en",
        reasons=["Best overall", "Budget pick"],
        include_image=False,
    )
    assert "### 1. Mechanical Gaming Keyboard" in md
    assert "Budget Keyboard" in md
    assert "Why it fits" in md
    assert "![" not in md


def test_build_shopping_chat_content_recommendation_markdown():
    products = [
        _sample_product(),
        _sample_product(id="p2", title_en="Budget Keyboard", price=1_950_000, rating=4.2),
        _sample_product(id="p3", title_en="Premium Keyboard", price=3_400_000, rating=4.6),
    ]
    content = build_shopping_chat_content(
        "Here are strong gift options.",
        products=products,
        reasons=["Balanced pick", "Lower price", "Higher rating"],
        language="en",
        render_mode="markdown",
        include_image=True,
        intent="gift_recommendation",
    )
    assert "Here are strong gift options." in content
    assert "Product showcase" in content or "### 1." in content
    assert "![Mechanical Gaming Keyboard]" in content
    assert "| Product | Price | Rating |" in content
    assert "I can also narrow this" in content


def test_build_shopping_chat_content_plain_mode():
    content = build_shopping_chat_content(
        "گزینه‌ها:",
        products=[_sample_product()],
        language="fa",
        render_mode="plain",
        include_image=True,
        intent="product_search",
    )
    assert "کیبورد گیمینگ مکانیکی" in content
    assert "## " not in content
    assert "![" not in content


def test_widget_fallback_still_renders_cards():
    widget = ProductCardWidget(data=ProductCardData(product=_sample_product()))
    content = build_shopping_chat_content(
        "Top match:",
        widgets=[widget],
        language="en",
        render_mode="markdown",
        intent="product_detail",
    )
    assert "### Mechanical Gaming Keyboard" in content
    assert "View & buy on Digikala" in content


def test_openai_compat_returns_markdown_product_cards(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "conversation_id": "markdown-cards",
            "messages": [{"role": "user", "content": "I need a birthday gift under 3000000"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert set(body.keys()) >= {"id", "object", "created", "model", "choices", "usage"}
    assert "widgets" not in body
    content = body["choices"][0]["message"]["content"]
    assert "## " in content or "### " in content or "| Product |" in content or "| محصول |" in content
    assert "View product" in content or "مشاهده محصول" in content or "digikala.com" in content


def test_openai_compat_image_search_returns_card_friendly_content(client):
    import base64

    image_url = "data:image/jpeg;base64," + base64.b64encode(b"image-data").decode()
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "conversation_id": "markdown-image",
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
    assert content
    assert "digikala.com" in content or "### " in content or "![" in content or "- **" in content
