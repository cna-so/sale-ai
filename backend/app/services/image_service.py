from __future__ import annotations

from backend.app.models.domain import ImageAnalysisResult
from backend.app.tools.image_understanding import ImageUnderstandingTool


class ImageService:
    def __init__(self, tool: ImageUnderstandingTool) -> None:
        self._tool = tool

    async def analyze(self, image_data: bytes, content_type: str, instruction: str | None, locale: str) -> ImageAnalysisResult:
        result = await self._tool.run(
            image_data=image_data,
            content_type=content_type,
            instruction=instruction,
            locale=locale,
        )
        return result.data
