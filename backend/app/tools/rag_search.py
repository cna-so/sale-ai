from __future__ import annotations

from backend.app.models.domain import ToolResult
from backend.app.rag.retrieval_service import RetrievalService
from backend.app.tools.base import BaseTool


class RAGSearchTool(BaseTool):
    name = "rag_search"

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    async def run(self, query: str, top_k: int = 5) -> ToolResult:
        docs = await self._retrieval_service.retrieve(query=query, top_k=top_k)
        return ToolResult(tool_name=self.name, success=True, data=docs)
