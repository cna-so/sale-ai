from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ReActAction = Literal[
    "rag_search",
    "product_search",
    "image_search",
    "answer_directly",
    "stop",
]


def _coerce_action_input(value: Any) -> str:
    """Models often return action_input as an object; normalize to a string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("query", "q", "search_query", "input", "text", "instruction"):
            nested = value.get(key)
            if nested:
                return str(nested)
        if not value:
            return ""
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


class ReActDecision(BaseModel):
    """Validated controller output; never exposed in a user-facing response."""

    next_action: ReActAction
    action_input: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=240)
    should_continue: bool = False

    @field_validator("action_input", mode="before")
    @classmethod
    def normalize_action_input(cls, value: Any) -> str:
        return _coerce_action_input(value)


class ReActStep(BaseModel):
    """Compact, internal-only trace of a controller decision and observation."""

    iteration: int = Field(ge=1)
    action: ReActAction
    action_input: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=240)
    observation: str = Field(default="", max_length=500)

    @field_validator("action_input", mode="before")
    @classmethod
    def normalize_action_input(cls, value: Any) -> str:
        return _coerce_action_input(value)
