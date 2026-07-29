from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    # OpenRouter
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_chat_model: str = "google/gemini-2.5-flash-lite"
    openrouter_vision_model: str = "google/gemini-2.5-flash-lite"
    openrouter_embedding_model: str = "openai/text-embedding-3-small"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "shopping_assistant_documents"

    # Product provider
    product_provider: Literal["mock", "digikala"] = "mock"
    product_search_timeout_seconds: int = 20

    # File uploads
    max_upload_size_mb: int = 10

    # RAG
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50

    # Conversation
    chat_history_limit: int = 12

    # ReAct controller
    react_max_iterations: int = Field(default=3, ge=1, le=8)

    # Locale
    default_locale: str = "fa-IR"
    default_currency: str = "IRR"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
