"""ID generation for context items."""
from __future__ import annotations
import uuid


def new_id(prefix: str = "ctx") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
