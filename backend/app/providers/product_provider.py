from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.models.domain import ProductSearchResult


class ProductProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        ...
