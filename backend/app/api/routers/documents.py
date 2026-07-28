from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from backend.app.api.dependencies import get_indexing_service
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import FileSizeExceededError, UnsupportedFileTypeError
from backend.app.rag.indexing_service import IndexingService
from backend.app.schemas.documents import DocumentIndexRequest, DocumentIndexResponse, DocumentUploadResponse
from backend.app.utils.files import ensure_dir, safe_filename, validate_extension

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])

UPLOAD_DIR = Path("data/uploads")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
):
    filename = safe_filename(file.filename or "upload")
    try:
        validate_extension(filename)
    except ValueError as exc:
        raise UnsupportedFileTypeError(Path(filename).suffix)

    data = await file.read()
    if len(data) > settings.max_upload_size_bytes:
        raise FileSizeExceededError(settings.max_upload_size_mb)

    dest_dir = ensure_dir(UPLOAD_DIR)
    dest_path = dest_dir / filename
    dest_path.write_bytes(data)

    logger.info("Uploaded document '%s' (%d bytes)", filename, len(data))
    return DocumentUploadResponse(
        filename=filename,
        stored_path=str(dest_path),
        size_bytes=len(data),
    )


@router.post("/documents/index", response_model=DocumentIndexResponse)
async def index_document(
    body: DocumentIndexRequest,
    indexing_service: IndexingService = Depends(get_indexing_service),
    settings: Settings = Depends(get_settings),
):
    file_path = Path(body.file_path)
    if not file_path.is_absolute():
        candidate = Path("data/documents") / file_path
        if candidate.exists():
            file_path = candidate
        elif (UPLOAD_DIR / file_path).exists():
            file_path = UPLOAD_DIR / file_path

    collection = body.collection or settings.qdrant_collection
    result = await indexing_service.index_file(file_path=file_path, collection=collection)

    return DocumentIndexResponse(
        file_path=str(file_path),
        collection=result["collection"],
        chunks_indexed=result["chunks_indexed"],
        document_id=result["document_id"],
    )
