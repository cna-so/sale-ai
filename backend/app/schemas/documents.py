from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    filename: str
    stored_path: str
    size_bytes: int
    message: str = "File uploaded successfully"


class DocumentIndexRequest(BaseModel):
    file_path: str = Field(description="Path to file, relative to data/documents/ or absolute")
    collection: str | None = Field(default=None, description="Override Qdrant collection name")


class DocumentIndexResponse(BaseModel):
    file_path: str
    collection: str
    chunks_indexed: int
    document_id: str
    message: str = "Document indexed successfully"
