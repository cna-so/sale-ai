from __future__ import annotations

import base64
import json

from pydantic import ValidationError

from backend.app.core.exceptions import ImageProcessingError
from backend.app.models.domain import ImageAnalysisResult, ToolResult
from backend.app.prompts.image import IMAGE_PROMPT_EN, IMAGE_PROMPT_FA
from backend.app.services.llm_service import LLMService
from backend.app.tools.base import BaseTool


class ImageUnderstandingTool(BaseTool):
    name = "image_understanding"

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def run(
        self,
        image_data: bytes,
        content_type: str,
        instruction: str | None = None,
        locale: str = "fa-IR",
    ) -> ToolResult:
        prompt = IMAGE_PROMPT_FA if locale.startswith("fa") else IMAGE_PROMPT_EN
        if instruction:
            prompt += f"\nUser instruction: {instruction}"

        try:
            b64 = base64.b64encode(image_data).decode("ascii")
            raw = await self._llm.chat_with_image(
                text_prompt=prompt,
                image_base64=b64,
                content_type=content_type,
            )
            parsed = json.loads(raw)
            analysis = ImageAnalysisResult.model_validate(parsed)
            return ToolResult(tool_name=self.name, success=True, data=analysis)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ImageProcessingError(f"Vision model returned invalid structured output: {exc}") from exc
        except Exception as exc:
            raise ImageProcessingError(f"Failed to process image: {exc}") from exc
