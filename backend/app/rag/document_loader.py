from __future__ import annotations

import logging
from pathlib import Path

from backend.app.core.exceptions import DocumentLoadError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)


def load_document(file_path: str | Path) -> str:
    """
    Load a .txt, .md, or .pdf file and return its text content.
    Raises DocumentLoadError or UnsupportedFileTypeError on failure.
    """
    path = Path(file_path)
    if not path.exists():
        raise DocumentLoadError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            raise DocumentLoadError(f"Failed to read text file: {exc}") from exc

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            raise DocumentLoadError("pypdf is required to load PDF files.")
        except Exception as exc:
            raise DocumentLoadError(f"Failed to read PDF: {exc}") from exc

    raise UnsupportedFileTypeError(suffix)
