from __future__ import annotations

from backend.app.models.domain import Product
from backend.app.schemas.widgets import (
    ComparisonTableData,
    ComparisonTableWidget,
    ProductCardData,
    ProductCardWidget,
    ProductCarouselData,
    ProductCarouselWidget,
)


def _make_product(title: str = "کیبورد گیمینگ تست", price: int = 2_000_000) -> Product:
    return Product(
        id="test-id",
        title=title,
        title_en="Test Gaming Keyboard",
        price=price,
        currency="IRR",
        rating=4.3,
        review_count=50,
        product_url="https://www.digikala.com/product/dkp-test/",
        source="digikala",
    )


def test_product_card_widget_serialization():
    product = _make_product()
    widget = ProductCardWidget(data=ProductCardData(product=product))
    dumped = widget.model_dump()
    assert dumped["type"] == "product_card"
    assert dumped["data"]["product"]["title"] == "کیبورد گیمینگ تست"
    assert dumped["data"]["product"]["currency"] == "IRR"


def test_product_carousel_persian_title():
    products = [_make_product(f"محصول {i}") for i in range(3)]
    widget = ProductCarouselWidget(
        data=ProductCarouselData(title="محصولات پیشنهادی", products=products)
    )
    dumped = widget.model_dump()
    assert dumped["type"] == "product_carousel"
    assert dumped["data"]["title"] == "محصولات پیشنهادی"
    assert len(dumped["data"]["products"]) == 3


def test_comparison_table_widget():
    widget = ComparisonTableWidget(
        data=ComparisonTableData(
            title="مقایسه کیبوردها",
            columns=["محصول", "قیمت", "امتیاز"],
            rows=[["کیبورد A", "۲٬۰۰۰٬۰۰۰ تومان", "4.5"]],
        )
    )
    dumped = widget.model_dump()
    assert dumped["type"] == "comparison_table"
    assert dumped["data"]["columns"][0] == "محصول"
    assert len(dumped["data"]["rows"]) == 1


def test_widget_discriminated_union():
    from backend.app.schemas.chat import ChatResponse
    from backend.app.utils.ids import new_id

    card = ProductCardWidget(data=ProductCardData(product=_make_product()))
    resp = ChatResponse(
        conversation_id=new_id(),
        message_id=new_id(),
        answer="پاسخ آزمایشی",
        intent="product_search",
        widgets=[card],
    )
    serialized = resp.model_dump()
    assert serialized["widgets"][0]["type"] == "product_card"
