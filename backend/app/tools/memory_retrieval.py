from __future__ import annotations

from backend.app.models.domain import ToolResult
from backend.app.repositories.conversation_repository import ConversationRepository
from backend.app.tools.base import BaseTool


class MemoryRetrievalTool(BaseTool):
    name = "memory_retrieval"

    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def run(self, conversation_id: str, last_n: int = 12) -> ToolResult:
        messages = await self._repository.list_messages(conversation_id)
        return ToolResult(tool_name=self.name, success=True, data=messages[-last_n:])
