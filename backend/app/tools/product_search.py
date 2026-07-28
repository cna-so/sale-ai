from __future__ import annotations

from backend.app.models.domain import ToolResult
from backend.app.services.product_service import ProductService
from backend.app.tools.base import BaseTool


class ProductSearchTool(BaseTool):
    name = "product_search"

    def __init__(self, product_service: ProductService) -> None:
        self._product_service = product_service

    async def run(self, query: str, max_results: int = 5) -> ToolResult:
        result = await self._product_service.search(query=query, max_results=max_results)
        return ToolResult(tool_name=self.name, success=True, data=result)
