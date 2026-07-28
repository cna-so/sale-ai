from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.models.domain import Product, ProductSearchResult, Recommendation
from backend.app.providers.product_provider import ProductProvider
from backend.app.utils.language import detect_language, format_price_toman, parse_price_constraints


class ProductService:
    def __init__(self, provider: ProductProvider) -> None:
        self._provider = provider

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        return await self._provider.search(query=query, max_results=max_results)

    def filter_by_price(self, products: list[Product], min_toman: int | None, max_toman: int | None) -> list[Product]:
        filtered = products
        if min_toman is not None:
            filtered = [p for p in filtered if p.price >= min_toman]
        if max_toman is not None:
            filtered = [p for p in filtered if p.price <= max_toman]
        return filtered
