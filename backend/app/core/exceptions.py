from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 500) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFIGURATION_ERROR", 500)


class LLMError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "LLM_ERROR", 502)


class EmbeddingError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "EMBEDDING_ERROR", 502)


class VectorStoreError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "VECTOR_STORE_ERROR", 503)


class ProductProviderError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "PRODUCT_PROVIDER_ERROR", 503)


class DocumentLoadError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "DOCUMENT_LOAD_ERROR", 422)


class UnsupportedFileTypeError(AppError):
    def __init__(self, file_type: str) -> None:
        super().__init__(f"Unsupported file type: {file_type}", "UNSUPPORTED_FILE_TYPE", 415)


class FileSizeExceededError(AppError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(f"File exceeds maximum size of {max_mb}MB", "FILE_TOO_LARGE", 413)


class ConversationNotFoundError(AppError):
    def __init__(self, conversation_id: str) -> None:
        super().__init__(f"Conversation not found: {conversation_id}", "CONVERSATION_NOT_FOUND", 404)


class ImageProcessingError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "IMAGE_PROCESSING_ERROR", 422)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
    )
