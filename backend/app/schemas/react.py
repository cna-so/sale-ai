from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReActAction = Literal[
    "rag_search",
    "product_search",
    "image_search",
    "answer_directly",
    "stop",
]


class ReActDecision(BaseModel):
    """Validated controller output; never exposed in a user-facing response."""

    next_action: ReActAction
    action_input: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=240)
    should_continue: bool = False


class ReActStep(BaseModel):
    """Compact, internal-only trace of a controller decision and observation."""

    iteration: int = Field(ge=1)
    action: ReActAction
    action_input: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=240)
    observation: str = Field(default="", max_length=500)
