from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.models.domain import ToolResult


class BaseTool(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, *args, **kwargs) -> ToolResult:
        ...
