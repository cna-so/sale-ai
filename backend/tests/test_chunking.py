from __future__ import annotations

from backend.app.rag.chunking import chunk_text


def test_chunk_text_terminates_on_short_documents():
    text = "Short shopping guide about headphones and warranties."
    chunks = chunk_text(
        text=text,
        source="guide.md",
        document_id="doc-1",
        title="Guide",
        chunk_size=500,
        chunk_overlap=50,
    )

    assert len(chunks) == 1
    assert chunks[0].content == text


def test_chunk_text_terminates_with_overlap_on_long_documents():
    text = ("Word " * 400).strip()
    chunks = chunk_text(
        text=text,
        source="long.md",
        document_id="doc-2",
        title="Long",
        chunk_size=100,
        chunk_overlap=20,
    )

    assert 2 <= len(chunks) <= 30
    assert all(chunk.content for chunk in chunks)
