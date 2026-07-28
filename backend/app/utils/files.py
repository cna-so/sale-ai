from __future__ import annotations

import os
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def validate_extension(filename: str) -> str:
    """Return the lowercased extension or raise ValueError."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")
    return ext


def safe_filename(filename: str) -> str:
    """Strip directory traversal from an uploaded filename."""
    return os.path.basename(filename)
