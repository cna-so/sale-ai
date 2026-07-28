from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.vectorstore.qdrant_client import check_qdrant_health, get_qdrant_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    qdrant_ok = False
    try:
        client = get_qdrant_client(settings)
        qdrant_ok = await check_qdrant_health(client)
    except Exception:
        pass

    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_configured": settings.is_openrouter_configured,
        "product_provider": settings.product_provider,
        "qdrant": "healthy" if qdrant_ok else "unreachable",
        "models": {
            "chat": settings.openrouter_chat_model,
            "vision": settings.openrouter_vision_model,
            "embedding": settings.openrouter_embedding_model,
        },
    }
