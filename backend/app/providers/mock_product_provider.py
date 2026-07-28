from __future__ import annotations

import hashlib
import uuid

from backend.app.models.domain import Product, ProductSearchResult
from backend.app.providers.product_provider import ProductProvider


def _stable_id(seed: str) -> str:
    """Derive a stable UUID from a seed string so mock product IDs never change
    between calls, enabling cross-turn correlation (e.g. recommended_product_ids).
    """
    digest = hashlib.md5(seed.encode()).hexdigest()
    return str(uuid.UUID(digest))


_MOCK_PRODUCTS: list[Product] = [
    Product(
        id=_stable_id("mock-k552"),
        title="کیبورد گیمینگ مکانیکی ردراگون مدل K552 Kumara",
        title_en="Redragon K552 Kumara Mechanical Keyboard",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-keyboard-1.jpg",
        price=2_850_000,
        currency="IRR",
        rating=4.5,
        review_count=234,
        product_url="https://www.digikala.com/product/dkp-mock-k552/",
        source="digikala",
    ),
    Product(
        id=_stable_id("mock-gk601"),
        title="کیبورد گیمینگ گرین مدل GK601-RGB",
        title_en="Green GK601 RGB Gaming Keyboard",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-keyboard-2.jpg",
        price=1_950_000,
        currency="IRR",
        rating=4.2,
        review_count=118,
        product_url="https://www.digikala.com/product/dkp-mock-gk601/",
        source="digikala",
    ),
    Product(
        id=_stable_id("mock-g213"),
        title="کیبورد گیمینگ لاجیتک مدل G213 Prodigy",
        title_en="Logitech G213 Prodigy",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-keyboard-3.jpg",
        price=3_400_000,
        currency="IRR",
        rating=4.6,
        review_count=310,
        product_url="https://www.digikala.com/product/dkp-mock-g213/",
        source="digikala",
    ),
    Product(
        id=_stable_id("mock-whch520"),
        title="هدفون بی‌سیم سونی مدل WH-CH520",
        title_en="Sony WH-CH520 Wireless Headphones",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-headphone-1.jpg",
        price=2_200_000,
        currency="IRR",
        rating=4.4,
        review_count=189,
        product_url="https://www.digikala.com/product/dkp-mock-whch520/",
        source="digikala",
    ),
    Product(
        id=_stable_id("mock-deathadder"),
        title="ماوس گیمینگ ریزر مدل DeathAdder Essential",
        title_en="Razer DeathAdder Essential",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-mouse-1.jpg",
        price=1_750_000,
        currency="IRR",
        rating=4.7,
        review_count=402,
        product_url="https://www.digikala.com/product/dkp-mock-deathadder/",
        source="digikala",
    ),
    Product(
        id=_stable_id("mock-vivobook15"),
        title="لپ‌تاپ ایسوس مدل VivoBook 15 X1502ZA",
        title_en="Asus VivoBook 15 X1502ZA Laptop",
        image_url="https://dkstatics-public.digikala.com/digikala-products/mock-laptop-1.jpg",
        price=28_500_000,
        currency="IRR",
        rating=4.3,
        review_count=95,
        product_url="https://www.digikala.com/product/dkp-mock-vivobook15/",
        source="digikala",
    ),
]


class MockProductProvider(ProductProvider):
    name = "mock"

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        q = query.lower()
        tokens = q.split()

        filtered = [
            p
            for p in _MOCK_PRODUCTS
            if any(token in (p.title + " " + p.title_en).lower() for token in tokens)
        ]
        final = filtered[:max_results] if filtered else _MOCK_PRODUCTS[:max_results]
        return ProductSearchResult(
            products=final,
            query=query,
            provider=self.name,
            total_found=len(final),
        )
