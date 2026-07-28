#!/usr/bin/env python3
"""
Copy seed documents to data/documents/ if not already present.
Useful for fresh Docker volumes.
"""
from __future__ import annotations

import shutil
from pathlib import Path

SEED_DIR = Path("data/documents")
FILES = [
    "sample_product_guide.md",
    "sample_return_policy.md",
    "sample_headphones.md",
]


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    for fname in FILES:
        dest = SEED_DIR / fname
        if dest.exists():
            print(f"Already exists: {dest}")
        else:
            print(f"Seed file missing: {dest}")


if __name__ == "__main__":
    main()
