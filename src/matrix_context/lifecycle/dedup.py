"""Write-time duplicate detection for durable agent memory."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Optional

from ..schema.item import ContextItem


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def find_duplicate(content: str, items: Iterable[ContextItem], *,
                   expert: str | None = None, scope: str | None = None,
                   threshold: float = 0.94) -> Optional[ContextItem]:
    best = None
    best_score = threshold
    for item in items:
        if not item.is_live():
            continue
        if expert and item.expert != expert:
            continue
        if scope and item.scope != scope:
            continue
        score = similarity(content, item.content)
        if score >= best_score:
            best, best_score = item, score
    return best


def is_duplicate(content: str, items: Iterable[ContextItem], **kwargs) -> bool:
    return find_duplicate(content, items, **kwargs) is not None
