from __future__ import annotations

import uuid


def new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())
