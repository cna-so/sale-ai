from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    source: str
    document_id: str
    title: str = ""


def chunk_text(
    text: str,
    source: str,
    document_id: str,
    title: str = "",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[TextChunk]:
    """
    Split *text* into overlapping chunks.
    Uses a simple character-level sliding window.
    Sentence boundaries are preferred when possible.
    """
    if not text.strip():
        return []

    chunks: list[TextChunk] = []
    start = 0
    idx = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        # Try to break at a paragraph or sentence boundary
        if end < length:
            for boundary in ("\n\n", "\n", ". ", ".\n", "! ", "? "):
                pos = text.rfind(boundary, start, end)
                if pos != -1 and pos > start + chunk_overlap:
                    end = pos + len(boundary)
                    break

        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=idx,
                    source=source,
                    document_id=document_id,
                    title=title,
                )
            )
            idx += 1

        start = end - chunk_overlap
        if start >= end:  # safety guard
            break

    return chunks
