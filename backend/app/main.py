from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routers import chat, documents, health, history
from backend.app.api.routers.openai_compat import router as openai_compat_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError, app_error_handler, generic_error_handler
from backend.app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Shopping Assistant starting (env=%s)", settings.app_env)
    logger.info("Product provider: %s", settings.product_provider)
    logger.info("LLM configured: %s", settings.is_openrouter_configured)
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    Path("data/documents").mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Shopping Assistant",
    description="Multilingual AI shopping assistant with RAG, product search, and image understanding.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(history.router)

# OpenAI-compatible adapter for LibreChat and any OpenAI-spec client
app.include_router(openai_compat_router)
