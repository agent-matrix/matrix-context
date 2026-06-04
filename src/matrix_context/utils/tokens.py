"""Model-agnostic token estimation, good enough for budgeting."""
from __future__ import annotations


def approx_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.3))
