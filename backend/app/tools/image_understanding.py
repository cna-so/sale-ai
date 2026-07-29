from __future__ import annotations

import base64
import json
import logging
import re

from pydantic import ValidationError

from backend.app.core.exceptions import ImageProcessingError, LLMError
from backend.app.models.domain import ImageAnalysisResult, ToolResult
from backend.app.prompts.image import (
    IMAGE_PROMPT_EN,
    IMAGE_PROMPT_FA,
    IMAGE_DESC_PROMPT_EN,
    IMAGE_DESC_PROMPT_FA,
)
from backend.app.services.llm_service import LLMService
from backend.app.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _parse_vision_json(raw: str) -> dict:
    """Parse model output that should be JSON, including fenced / noisy replies."""
    text = (raw or "").strip()
    if not text:
        raise json.JSONDecodeError("Expecting value", text, 0)

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed

    raise json.JSONDecodeError("Expecting value", text, 0)


def _analysis_from_plain_text(description: str, locale: str) -> ImageAnalysisResult:
    """Build a usable analysis when the model only returns free text."""
    text = " ".join((description or "").split()).strip()
    if not text:
        raise ImageProcessingError("Vision model returned empty description.")

    # Prefer a short search query: first sentence / clause, capped.
    query = re.split(r"[.!?\n،؛]", text, maxsplit=1)[0].strip()
    query = query[:80] or text[:80]
    return ImageAnalysisResult(
        product_category="product",
        concise_description=text[:280],
        visual_attributes=[],
        suggested_search_query=query,
        confidence=0.55,
    )


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
        is_fa = locale.startswith("fa")
        json_prompt = IMAGE_PROMPT_FA if is_fa else IMAGE_PROMPT_EN
        desc_prompt = IMAGE_DESC_PROMPT_FA if is_fa else IMAGE_DESC_PROMPT_EN
        if instruction:
            json_prompt += f"\nUser instruction: {instruction}"
            desc_prompt += f"\nUser instruction: {instruction}"

        b64 = base64.b64encode(image_data).decode("ascii")
        last_error: Exception | None = None

        # Attempt 1: ask for JSON without response_format (more reliable for vision).
        try:
            raw = await self._llm.chat_with_image(
                text_prompt=json_prompt,
                image_base64=b64,
                content_type=content_type,
                max_tokens=600,
            )
            parsed = _parse_vision_json(raw)
            analysis = ImageAnalysisResult.model_validate(parsed)
            return ToolResult(tool_name=self.name, success=True, data=analysis)
        except (json.JSONDecodeError, ValidationError, LLMError, ImageProcessingError) as exc:
            last_error = exc
            logger.warning("Vision JSON attempt failed: %s", exc)

        # Attempt 2: free-text product description → synthesize structured result.
        try:
            raw = await self._llm.chat_with_image(
                text_prompt=desc_prompt,
                image_base64=b64,
                content_type=content_type,
                max_tokens=250,
            )
            # If the model still returned JSON, prefer that.
            try:
                parsed = _parse_vision_json(raw)
                analysis = ImageAnalysisResult.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError):
                analysis = _analysis_from_plain_text(raw, locale)
            return ToolResult(tool_name=self.name, success=True, data=analysis)
        except (LLMError, ImageProcessingError, ValidationError) as exc:
            last_error = exc
            logger.warning("Vision description attempt failed: %s", exc)

        raise ImageProcessingError(
            f"Vision model returned invalid structured output: {last_error}"
        ) from last_error
