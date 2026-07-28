from __future__ import annotations

from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: APIError
